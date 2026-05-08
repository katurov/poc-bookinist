import os
import json
import asyncio
import httpx
import base64
import sys
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

from solders.keypair import Keypair
from x402 import x402Client, parse_payment_required
from x402.mechanisms.svm.exact import ExactSvmClientScheme
import x402.mechanisms.svm.exact.client as svm_client
from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
import binascii

# Load environment variables
def find_env():
    # Try looking in client/.env from the current working directory first
    if os.path.exists("client/.env"): return os.path.join(os.getcwd(), "client/.env")
    # Then try absolute path based on script location
    # .gemini/skills/expert-finder/scripts/expert_search.py -> 5 levels up to root
    base = os.path.abspath(__file__)
    for _ in range(5): base = os.path.dirname(base)
    path = os.path.join(base, "client", ".env")
    if os.path.exists(path): return path
    return None

env_path = find_env()
if env_path: load_dotenv(env_path)

PRIVATE_KEY_STR = os.getenv("CLIENT_PRIVATE_KEY")
if not PRIVATE_KEY_STR:
    print(json.dumps({"error": "CLIENT_PRIVATE_KEY not found in .env"}))
    sys.exit(1)

try:
    key_data = json.loads(PRIVATE_KEY_STR)
    CLIENT_KEYPAIR = Keypair.from_bytes(bytes(key_data))
except Exception as e:
    print(json.dumps({"error": f"Failed to parse private key: {e}"}))
    sys.exit(1)

# --- Patch x402 SDK for SOL support ---
def patched_create_payment_payload(self, requirements):
    network = str(requirements.network)
    client = self._get_client(network)
    extra = requirements.extra or {}
    fee_payer_str = extra.get("fee_payer") or extra.get("feePayer")
    mint = Pubkey.from_string(requirements.asset)
    payer_pubkey = Pubkey.from_string(self._signer.address)
    is_native_sol = (str(mint) == "11111111111111111111111111111111")
    
    if is_native_sol:
        token_program = Pubkey.from_string("11111111111111111111111111111111")
        decimals = 9
        source_ata = payer_pubkey
        dest_ata = Pubkey.from_string(requirements.pay_to)
        fee_payer = payer_pubkey
    else:
        if not fee_payer_str: raise ValueError("feePayer missing")
        fee_payer = Pubkey.from_string(fee_payer_str)
        mint_info = client.get_account_info(mint)
        mint_data = mint_info.value.data
        decimals = mint_data[44]
        from x402.mechanisms.svm.utils import derive_ata
        source_ata = Pubkey.from_string(derive_ata(self._signer.address, requirements.asset, str(mint_info.value.owner)))
        dest_ata = Pubkey.from_string(derive_ata(requirements.pay_to, requirements.asset, str(mint_info.value.owner)))
        token_program = mint_info.value.owner

    compute_budget_program = Pubkey.from_string(svm_client.COMPUTE_BUDGET_PROGRAM_ADDRESS)
    set_cu_limit_ix = Instruction(program_id=compute_budget_program, accounts=[], data=bytes([2]) + svm_client.DEFAULT_COMPUTE_UNIT_LIMIT.to_bytes(4, "little"))
    set_cu_price_ix = Instruction(program_id=compute_budget_program, accounts=[], data=bytes([3]) + svm_client.DEFAULT_COMPUTE_UNIT_PRICE_MICROLAMPORTS.to_bytes(8, "little"))

    amount = int(requirements.amount)
    if is_native_sol:
        transfer_ix = Instruction(program_id=token_program, accounts=[AccountMeta(source_ata, True, True), AccountMeta(dest_ata, False, True)], data=bytes([2, 0, 0, 0]) + amount.to_bytes(8, "little"))
    else:
        transfer_ix = Instruction(program_id=token_program, accounts=[AccountMeta(source_ata, False, True), AccountMeta(mint, False, False), AccountMeta(dest_ata, False, True), AccountMeta(payer_pubkey, True, False)], data=bytes([12]) + amount.to_bytes(8, "little") + bytes([decimals]))

    memo_ix = Instruction(program_id=Pubkey.from_string(svm_client.MEMO_PROGRAM_ADDRESS), accounts=[], data=binascii.hexlify(os.urandom(16)))
    blockhash = client.get_latest_blockhash().value.blockhash
    message = MessageV0.try_compile(payer=fee_payer, instructions=[set_cu_limit_ix, set_cu_price_ix, transfer_ix, memo_ix], address_lookup_table_accounts=[], recent_blockhash=blockhash)
    msg_bytes_with_version = bytes([0x80]) + bytes(message)
    client_signature = self._signer.keypair.sign_message(msg_bytes_with_version)
    signatures = [client_signature] if is_native_sol else [Signature.default(), client_signature]
    tx = VersionedTransaction.populate(message, signatures)
    return {"transaction": base64.b64encode(bytes(tx)).decode("utf-8")}

svm_client.ExactSvmScheme.create_payment_payload = patched_create_payment_payload

class SignerWrapper:
    def __init__(self, keypair): self._keypair = keypair
    @property
    def address(self) -> str: return str(self._keypair.pubkey())
    @property
    def keypair(self) -> Keypair: return self._keypair

x402_client = x402Client()
x402_client.register("solana:*", ExactSvmClientScheme(SignerWrapper(CLIENT_KEYPAIR)))

async def fetch_data(base_url, query, signature_payload=None):
    headers = {"payment-signature": signature_payload} if signature_payload else {}
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            # 1. Discovery
            manifest_res = await http_client.get(base_url)
            manifest_json = manifest_res.json()
            endpoint = manifest_json.get("usage", {}).get("endpoint", "/v1/search")
            parsed_base = urlparse(base_url)
            full_url = urljoin(f"{parsed_base.scheme}://{parsed_base.netloc}", endpoint)
            
            # 2. Request
            res = await http_client.post(full_url, json={"query": query, "limit": 5}, headers=headers)
            
            if res.status_code == 402:
                if signature_payload:
                    return {"error": "Payment rejected", "details": res.text}
                
                pay_req_header = res.headers.get("payment-required") or res.headers.get("Payment-Required")
                if not pay_req_header: return {"error": "Missing payment-required header"}
                
                payment_required = parse_payment_required(base64.b64decode(pay_req_header))
                payload = await x402_client.create_payment_payload(payment_required)
                payload_base64 = base64.b64encode(payload.model_dump_json().encode()).decode()
                
                # Retry with payment
                return await fetch_data(base_url, query, signature_payload=payload_base64)
            
            res.raise_for_status()
            return {"status": "success", "results": res.json()}
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: python expert_search.py <endpoint> <query>"}))
        sys.exit(1)
    
    endpoint = sys.argv[1]
    query = sys.argv[2]
    result = asyncio.run(fetch_data(endpoint, query))
    print(json.dumps(result, indent=2))

import os
import json
import sys
import asyncio
import httpx
import base64
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

from solders.keypair import Keypair
from x402 import x402Client, parse_payment_required
from x402.mechanisms.svm.exact import ExactSvmClientScheme

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(env_path)

# Configuration from .env
PRIVATE_KEY_STR = os.getenv("CLIENT_PRIVATE_KEY")
if not PRIVATE_KEY_STR:
    print("❌ ERROR: CLIENT_PRIVATE_KEY not found in .env")
    sys.exit(1)

try:
    key_data = json.loads(PRIVATE_KEY_STR)
    CLIENT_KEYPAIR = Keypair.from_bytes(bytes(key_data))
except Exception as e:
    print(f"❌ ERROR parsing CLIENT_PRIVATE_KEY: {e}")
    sys.exit(1)

# --- Patch x402 SDK for SOL support ---
import x402.mechanisms.svm.exact.client as svm_client
from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
import binascii

original_create_payload = svm_client.ExactSvmScheme.create_payment_payload

def patched_create_payment_payload(self, requirements):
    network = str(requirements.network)
    client = self._get_client(network)

    extra = requirements.extra or {}
    fee_payer_str = extra.get("fee_payer") or extra.get("feePayer")
    
    mint = Pubkey.from_string(requirements.asset)
    payer_pubkey = Pubkey.from_string(self._signer.address)
    
    is_native_sol = (str(mint) == "11111111111111111111111111111111")
    
    if is_native_sol:
        token_program = Pubkey.from_string("11111111111111111111111111111111") # System Program
        decimals = 9
        source_ata = payer_pubkey
        dest_ata = Pubkey.from_string(requirements.pay_to)
        # Use client as fee payer for SOL since local facilitator doesn't sign
        fee_payer = payer_pubkey
    else:
        if not fee_payer_str:
            raise ValueError("feePayer is required in requirements.extra for SVM transactions")
        fee_payer = Pubkey.from_string(fee_payer_str)
        # Replicate original logic for tokens
        mint_info = client.get_account_info(mint)
        if not mint_info.value:
            raise ValueError(f"Token mint not found: {requirements.asset}")
        mint_owner = str(mint_info.value.owner)
        if mint_owner == svm_client.TOKEN_PROGRAM_ADDRESS:
            token_program = Pubkey.from_string(svm_client.TOKEN_PROGRAM_ADDRESS)
        elif mint_owner == svm_client.TOKEN_2022_PROGRAM_ADDRESS:
            token_program = Pubkey.from_string(svm_client.TOKEN_2022_PROGRAM_ADDRESS)
        else:
            raise ValueError(f"Unknown token program: {mint_owner}")
        
        mint_data = mint_info.value.data
        decimals = mint_data[44]
        from x402.mechanisms.svm.utils import derive_ata
        source_ata = Pubkey.from_string(derive_ata(self._signer.address, requirements.asset, str(token_program)))
        dest_ata = Pubkey.from_string(derive_ata(requirements.pay_to, requirements.asset, str(token_program)))

    compute_budget_program = Pubkey.from_string(svm_client.COMPUTE_BUDGET_PROGRAM_ADDRESS)
    set_cu_limit_data = bytes([2]) + svm_client.DEFAULT_COMPUTE_UNIT_LIMIT.to_bytes(4, "little")
    set_cu_limit_ix = Instruction(program_id=compute_budget_program, accounts=[], data=set_cu_limit_data)

    set_cu_price_data = bytes([3]) + svm_client.DEFAULT_COMPUTE_UNIT_PRICE_MICROLAMPORTS.to_bytes(8, "little")
    set_cu_price_ix = Instruction(program_id=compute_budget_program, accounts=[], data=set_cu_price_data)

    amount = int(requirements.amount)
    if is_native_sol:
        # System Program Transfer
        transfer_data = bytes([2, 0, 0, 0]) + amount.to_bytes(8, "little")
        transfer_ix = Instruction(
            program_id=token_program,
            accounts=[
                AccountMeta(source_ata, is_signer=True, is_writable=True),
                AccountMeta(dest_ata, is_signer=False, is_writable=True),
            ],
            data=transfer_data,
        )
    else:
        # TransferChecked
        transfer_data = bytes([12]) + amount.to_bytes(8, "little") + bytes([decimals])
        transfer_ix = Instruction(
            program_id=token_program,
            accounts=[
                AccountMeta(source_ata, is_signer=False, is_writable=True),
                AccountMeta(mint, is_signer=False, is_writable=False),
                AccountMeta(dest_ata, is_signer=False, is_writable=True),
                AccountMeta(payer_pubkey, is_signer=True, is_writable=False),
            ],
            data=transfer_data,
        )

    memo_ix = Instruction(
        program_id=Pubkey.from_string(svm_client.MEMO_PROGRAM_ADDRESS),
        accounts=[],
        data=binascii.hexlify(os.urandom(16)),
    )

    blockhash = client.get_latest_blockhash().value.blockhash
    message = MessageV0.try_compile(
        payer=fee_payer,
        instructions=[set_cu_limit_ix, set_cu_price_ix, transfer_ix, memo_ix],
        address_lookup_table_accounts=[],
        recent_blockhash=blockhash,
    )
    msg_bytes_with_version = bytes([0x80]) + bytes(message)
    client_signature = self._signer.keypair.sign_message(msg_bytes_with_version)
    
    if is_native_sol:
        # Client is the ONLY signer (at index 0)
        signatures = [client_signature]
    else:
        # Client is at index 1, fee_payer placeholder at index 0
        signatures = [Signature.default(), client_signature]
        
    tx = VersionedTransaction.populate(message, signatures)
    tx_base64 = base64.b64encode(bytes(tx)).decode("utf-8")
    return {"transaction": tx_base64}

svm_client.ExactSvmScheme.create_payment_payload = patched_create_payment_payload
# --- End Patch ---

# Initialize x402 client
class SignerWrapper:
    def __init__(self, keypair):
        self._keypair = keypair
    
    @property
    def address(self) -> str:
        return str(self._keypair.pubkey())
    
    @property
    def keypair(self) -> Keypair:
        return self._keypair

    def sign_transaction(self, tx):
        # The x402 library actually handles the signing itself using self._signer.keypair.sign_message
        # as seen in ExactSvmScheme.create_payment_payload.
        # However, we implement this for protocol completeness.
        from solders.transaction import VersionedTransaction
        # This is a bit complex for a wrapper, but x402 V2.5.0 mainly uses .keypair
        return tx

x402_client = x402Client()
x402_client.register("solana:*", ExactSvmClientScheme(SignerWrapper(CLIENT_KEYPAIR)))

async def fetch_data(base_url, query, signature_payload=None, depth=0):
    """
    Fetches data from an x402-enabled provider using automated payment handling.
    """
    # Strictly one payment attempt to avoid loops
    if depth > 1:
        print("🛑 Maximum payment attempts reached. Stopping to prevent loop.")
        return

    headers = {}
    if signature_payload:
        # Use lowercase as seen in x402 examples
        headers["payment-signature"] = signature_payload
        print(f"🔑 Retrying with x402 payment payload...")

    print(f"🔗 Connecting to provider at: {base_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            # 1. Get manifest (Discovery)
            print(f"📡 Requesting manifest from {base_url}...")
            manifest_res = await http_client.get(base_url)
            manifest_res.raise_for_status()
            manifest_json = manifest_res.json()
            
            usage = manifest_json.get("usage", {})
            endpoint = usage.get("endpoint")
            method = usage.get("method", "POST")
            
            if not endpoint:
                print("❌ ERROR: Manifest missing endpoint.")
                return

            parsed_base = urlparse(base_url)
            domain_root = f"{parsed_base.scheme}://{parsed_base.netloc}"
            full_url = urljoin(domain_root, endpoint)
            
            # 2. Perform the data request
            print(f"🚀 Sending {method} request to {full_url}")
            
            if method == "POST":
                payload = {"query": query, "limit": 3}
                res = await http_client.post(full_url, json=payload, headers=headers)
            else:
                params = {"query": query}
                res = await http_client.get(full_url, params=params, headers=headers)
                
            # 3. Handle 402 Payment Required
            if res.status_code == 402:
                if signature_payload:
                    print("❌ Payment payload was rejected by server.")
                    print(f"Server response: {res.text}")
                    return

                print("🛑 HTTP 402: Payment Required!")
                pay_req_header = res.headers.get("payment-required")
                if not pay_req_header:
                    # Fallback to Title-Case
                    pay_req_header = res.headers.get("Payment-Required")
                
                if not pay_req_header:
                    print("❌ Missing 'payment-required' header in 402 response.")
                    return

                try:
                    # Decode and parse requirements
                    pr_data = base64.b64decode(pay_req_header)
                    payment_required = parse_payment_required(pr_data)
                    
                    print("✍️  Generating x402 payment payload (Solana)...")
                    # Create payment payload using x402 SDK
                    payload = await x402_client.create_payment_payload(payment_required)
                    
                    # Serialize payload to base64 for the header
                    payload_json = payload.model_dump_json()
                    payload_base64 = base64.b64encode(payload_json.encode()).decode()
                    
                    # Recursive retry with payment
                    return await fetch_data(base_url, query, signature_payload=payload_base64, depth=depth+1)
                except Exception as e:
                    print(f"❌ x402 Payment process failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return
            
            # Handle other errors
            res.raise_for_status()
            
            # 4. Success - Parse and display results
            results = res.json()
            
            print(f"\n✅ Data Received:")
            print("=" * 60)
            
            # Handle both list and dict results (some servers wrap results)
            items = results if isinstance(results, list) else results.get("results", [])
            
            if not items:
                print("No results found.")
            
            for i, item in enumerate(items, 1):
                name = item.get('name') or item.get('title') or "Unknown Item"
                score = item.get('rerank_score') or item.get('score') or "N/A"
                review = item.get('gault_millau_review') or item.get('description') or ""
                
                print(f"[{i}] {name}")
                print(f"    ⭐ Score/Relevance: {score}")
                if review:
                    snippet = review[:150].replace('\n', ' ')
                    print(f"    📖 Info: {snippet}...")
                print("-" * 60)
                
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"❌ Network Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Usage: python fetch_data.py "query" "http://server-url/v1/"
    query = sys.argv[1] if len(sys.argv) > 1 else "burger"
    target_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3333/v1/"
    
    # Ensure target_url ends with slash for urljoin
    if not target_url.endswith('/'):
        target_url += '/'
        
    asyncio.run(fetch_data(target_url, query))

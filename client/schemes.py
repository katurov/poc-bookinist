import os
import binascii
import base64
from typing import Dict, Any

from solders.instruction import AccountMeta, Instruction
from solders.pubkey import Pubkey
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from x402.mechanisms.svm.exact import ExactSvmClientScheme

# Constants inherited from x402 internals (usually private or hard to reach)
MEMO_PROGRAM_ADDRESS = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
COMPUTE_BUDGET_PROGRAM_ADDRESS = "ComputeBudget111111111111111111111111111111"
SYSTEM_PROGRAM_ADDRESS = "11111111111111111111111111111111"
DEFAULT_COMPUTE_UNIT_LIMIT = 200_000
DEFAULT_COMPUTE_UNIT_PRICE_MICROLAMPORTS = 1_000

class NativeSolSvmScheme(ExactSvmClientScheme):
    """
    Extends ExactSvmClientScheme to properly handle native SOL transfers 
    without monkey-patching the base library.
    """
    
    async def create_payment_payload(self, requirements: Any) -> Dict[str, str]:
        mint = str(requirements.asset)
        
        # If it's not native SOL, fall back to the standard implementation
        if mint != SYSTEM_PROGRAM_ADDRESS:
            return await super().create_payment_payload(requirements)

        # Handle Native SOL logic
        network = str(requirements.network)
        client = self._get_client(network)

        payer_pubkey = Pubkey.from_string(self._signer.address)
        dest_ata = Pubkey.from_string(requirements.pay_to)
        
        # In native SOL transfer via System Program, the payer is the fee payer
        fee_payer = payer_pubkey

        # 1. Compute Budget Instructions
        compute_budget_program = Pubkey.from_string(COMPUTE_BUDGET_PROGRAM_ADDRESS)
        set_cu_limit_data = bytes([2]) + DEFAULT_COMPUTE_UNIT_LIMIT.to_bytes(4, "little")
        set_cu_limit_ix = Instruction(program_id=compute_budget_program, accounts=[], data=set_cu_limit_data)

        set_cu_price_data = bytes([3]) + DEFAULT_COMPUTE_UNIT_PRICE_MICROLAMPORTS.to_bytes(8, "little")
        set_cu_price_ix = Instruction(program_id=compute_budget_program, accounts=[], data=set_cu_price_data)

        # 2. System Program Transfer Instruction
        amount = int(requirements.amount)
        transfer_data = bytes([2, 0, 0, 0]) + amount.to_bytes(8, "little")
        transfer_ix = Instruction(
            program_id=Pubkey.from_string(SYSTEM_PROGRAM_ADDRESS),
            accounts=[
                AccountMeta(payer_pubkey, is_signer=True, is_writable=True),
                AccountMeta(dest_ata, is_signer=False, is_writable=True),
            ],
            data=transfer_data,
        )

        # 3. Memo Instruction
        memo_ix = Instruction(
            program_id=Pubkey.from_string(MEMO_PROGRAM_ADDRESS),
            accounts=[],
            data=binascii.hexlify(os.urandom(16)),
        )

        # Build and sign transaction
        blockhash = client.get_latest_blockhash().value.blockhash
        message = MessageV0.try_compile(
            payer=fee_payer,
            instructions=[set_cu_limit_ix, set_cu_price_ix, transfer_ix, memo_ix],
            address_lookup_table_accounts=[],
            recent_blockhash=blockhash,
        )
        
        # VersionedTransaction requires a specific prefix for signing message bytes
        msg_bytes_with_version = bytes([0x80]) + bytes(message)
        client_signature = self._signer.keypair.sign_message(msg_bytes_with_version)
        
        # Signatures array: Fee payer is at index 0
        signatures = [client_signature]
        
        tx = VersionedTransaction.populate(message, signatures)
        tx_base64 = base64.b64encode(bytes(tx)).decode("utf-8")
        
        return {"transaction": tx_base64}

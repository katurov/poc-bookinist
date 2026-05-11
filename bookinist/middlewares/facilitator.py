import os
from x402.schemas import VerifyResponse, SettleResponse, SupportedResponse, SupportedKind
from x402.mechanisms.svm.utils import decode_transaction_from_payload
from x402.mechanisms.svm.types import ExactSvmPayload
from solana.rpc.api import Client
from solders.transaction import VersionedTransaction
from solders.signature import Signature
import base64

class LocalSvmFacilitator:
    def __init__(self, network_id: str, recipient_address: str, rpc_url: str = "https://api.devnet.solana.com"):
        self.network_id = network_id
        self.recipient_address = recipient_address
        self.client = Client(rpc_url)

    async def verify(self, payload, requirements):
        """
        Verifies the transaction payload.
        TODO: Add commitment check (confirmed/finalized) by fetching the transaction from the network
        after it's been sent, to ensure it wasn't rolled back or failed.
        """
        print(f"DEBUG LOCAL FACILITATOR: Verifying {requirements.asset}...")
        try:
            svm_payload = ExactSvmPayload.from_dict(payload.payload)
            tx = decode_transaction_from_payload(svm_payload)
            
            # Check for native SOL transfer
            if str(requirements.asset) == "11111111111111111111111111111111":
                msg = tx.message
                static_accounts = list(msg.account_keys)
                for ix in msg.instructions:
                    program = static_accounts[ix.program_id_index]
                    if str(program) == "11111111111111111111111111111111":
                        data = bytes(ix.data)
                        if len(data) >= 12 and data[0] == 2: # Transfer
                            amount = int.from_bytes(data[4:12], "little")
                            if amount >= int(requirements.amount):
                                dest = static_accounts[ix.accounts[1]]
                                if str(dest) == str(requirements.pay_to):
                                    payer = str(static_accounts[ix.accounts[0]])
                                    print(f"DEBUG LOCAL FACILITATOR: SOL Transfer verified! Payer: {payer}")
                                    return VerifyResponse(is_valid=True, payer=payer)
                
                return VerifyResponse(is_valid=False, invalid_reason="no_sol_transfer_found", payer="")
            
            return VerifyResponse(is_valid=False, invalid_reason="unsupported_asset", payer="")
        except Exception as e:
            print(f"DEBUG LOCAL FACILITATOR: Error during verify: {e}")
            return VerifyResponse(is_valid=False, invalid_reason=str(e), payer="")

    async def settle(self, payload, requirements):
        """
        Submits the transaction to the network.
        """
        print(f"DEBUG LOCAL FACILITATOR: Settling {requirements.asset}...")
        try:
            svm_payload = ExactSvmPayload.from_dict(payload.payload)
            tx_bytes = base64.b64decode(svm_payload.transaction)
            
            # Note: We use send_raw_transaction. In a production environment, we should 
            # check the status of the transaction here or in a background task.
            res = self.client.send_raw_transaction(tx_bytes)
            sig = str(res.value)
            print(f"DEBUG LOCAL FACILITATOR: Settlement success! Signature: {sig}")
            
            # TODO: Wait for confirmation (e.g. self.client.confirm_transaction(sig, commitment="confirmed"))
            
            return SettleResponse(success=True, transaction=sig, network=str(requirements.network), payer="")
        except Exception as e:
            print(f"DEBUG LOCAL FACILITATOR: Error during settle: {e}")
            return SettleResponse(success=False, error_reason=str(e), transaction="", network=str(requirements.network), payer="")

    def get_supported(self):
        return SupportedResponse(kinds=[
            SupportedKind(x402_version=2, scheme="exact", network=self.network_id, extra={"feePayer": self.recipient_address})
        ])

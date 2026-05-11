import json
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solders.transaction import Transaction
from solders.message import Message
from solders.system_program import transfer, TransferParams
from solana.rpc.api import Client
from solders.keypair import Keypair
import time
from typing import Optional

from core.models import AgentManifest

class AgentRegistryService:
    def __init__(self, rpc_url: str, private_key_data: list):
        """
        Initializes the service.
        :param rpc_url: Solana RPC URL
        :param private_key_data: List of bytes representing the private key
        """
        self.client = Client(rpc_url)
        self.keypair = Keypair.from_bytes(bytes(private_key_data))
        self.memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

    def publish_manifest(self, manifest: AgentManifest, registry_pubkey: Optional[str] = None, retries: int = 3, delay_sec: int = 2) -> Optional[str]:
        """
        Publishes the AgentManifest to the Solana network using the Memo program.
        If registry_pubkey is provided, includes a 0-lamport transfer instruction to make it discoverable.
        Includes retry logic for network resilience.
        """
        manifest_json = manifest.model_dump_json()
        print(f"Publishing Manifest: {manifest_json}")

        instructions = []

        if registry_pubkey:
            registry_pk = Pubkey.from_string(registry_pubkey)
            transfer_ix = transfer(TransferParams(
                from_pubkey=self.keypair.pubkey(),
                to_pubkey=registry_pk,
                lamports=0
            ))
            instructions.append(transfer_ix)

        memo_ix = Instruction(
            program_id=self.memo_program_id,
            accounts=[],
            data=manifest_json.encode('utf-8')
        )
        instructions.append(memo_ix)

        for attempt in range(retries):
            try:
                recent_blockhash = self.client.get_latest_blockhash().value.blockhash
                message = Message(instructions, self.keypair.pubkey())
                txn = Transaction([self.keypair], message, recent_blockhash)
                
                response = self.client.send_transaction(txn)
                return str(response.value)
            except Exception as e:
                print(f"Attempt {attempt + 1}/{retries} failed: {e}")
                if attempt < retries - 1:
                    print(f"Retrying in {delay_sec} seconds...")
                    time.sleep(delay_sec)
                else:
                    print("Failed to publish manifest after all retries.")
                    raise

        return None

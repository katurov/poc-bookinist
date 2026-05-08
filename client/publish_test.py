import os
import json
from typing import List
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solana.transaction import Transaction
from solders.system_program import transfer, TransferParams

# Load environment variables
load_dotenv()

# Configuration
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
REGISTRY_PUBKEY = Pubkey.from_string(os.getenv("REGISTRY_PUBKEY"))
CLIENT_PRIVATE_KEY = json.loads(os.getenv("CLIENT_PRIVATE_KEY"))
CLIENT_KEYPAIR = Keypair.from_bytes(bytes(CLIENT_PRIVATE_KEY))

class AgentManifest(BaseModel):
    agent_name: str
    niche: str
    tags: List[str]
    base_price_usdc: float
    endpoint: HttpUrl
    description: str

def publish_test_manifest():
    client = Client(SOLANA_RPC_URL)
    
    # Example manifest
    manifest = AgentManifest(
        agent_name="BalkanGastroNode",
        niche="Gastronomy and wines",
        tags=["food", "serbia", "datasets"],
        base_price_usdc=0.5,
        endpoint="https://api.balkangastro.com/v1/",
        description="Detailed ratings and datasets of Serbian restaurants and wineries."
    )
    
    manifest_json = manifest.model_dump_json()
    print(f"📦 Prepared Manifest: {manifest_json}")

    # 1. Memo Instruction
    MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
    memo_ix = Instruction(
        program_id=MEMO_PROGRAM_ID,
        accounts=[],
        data=manifest_json.encode('utf-8')
    )

    # 2. Transfer Instruction (0 SOL to registry to make the transaction discoverable)
    transfer_ix = transfer(TransferParams(
        from_pubkey=CLIENT_KEYPAIR.pubkey(),
        to_pubkey=REGISTRY_PUBKEY,
        lamports=0
    ))

    # Wrap in transaction
    txn = Transaction().add(transfer_ix).add(memo_ix)

    print(f"🚀 Publishing to registry {REGISTRY_PUBKEY}...")
    try:
        # Get recent blockhash
        res = client.get_latest_blockhash()
        txn.recent_blockhash = res.value.blockhash
        
        response = client.send_transaction(txn, CLIENT_KEYPAIR)
        print(f"✅ Success! Transaction Hash: {response.value}")
    except Exception as e:
        print(f"❌ Failed to send transaction: {e}")
        print("Note: Make sure your account has SOL for fees on Devnet!")

if __name__ == "__main__":
    publish_test_manifest()

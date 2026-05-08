import os
import json
from typing import List
from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solders.transaction import Transaction
from solders.message import Message
from solders.system_program import transfer, TransferParams

# Load environment variables from .env file
load_dotenv()

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    solana_private_key: str
    solana_rpc_url: str = "https://api.devnet.solana.com"
    registry_pubkey: str
    
    agent_name: str
    agent_niche: str
    agent_tags: str  # Comma separated
    agent_base_price_usdc: float
    agent_endpoint: HttpUrl
    agent_description: str

class AgentManifest(BaseModel):
    agent_name: str
    niche: str
    tags: List[str]
    base_price_usdc: float
    endpoint: HttpUrl
    description: str

def get_keypair_from_string(key_str: str) -> Keypair:
    try:
        key_data = json.loads(key_str)
        if isinstance(key_data, list):
            return Keypair.from_bytes(bytes(key_data))
    except json.JSONDecodeError:
        pass
    raise ValueError("Private key format not recognized. Please use a JSON array of bytes.")

def main():
    settings = AppSettings()
    
    # Prepare Manifest
    manifest = AgentManifest(
        agent_name=settings.agent_name,
        niche=settings.agent_niche,
        tags=[t.strip() for t in settings.agent_tags.split(",")],
        base_price_usdc=settings.agent_base_price_usdc,
        endpoint=settings.agent_endpoint,
        description=settings.agent_description
    )
    
    manifest_json = manifest.model_dump_json()
    print(f"Prepared Manifest: {manifest_json}")

    # Solana setup
    client = Client(settings.solana_rpc_url)
    try:
        my_keypair = get_keypair_from_string(settings.solana_private_key)
    except Exception as e:
        print(f"Error loading keypair: {e}")
        return

    # Official Memo Program ID
    MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")

    # 1. Transfer Instruction (0 SOL to registry to make it discoverable)
    registry_pubkey = Pubkey.from_string(settings.registry_pubkey)
    transfer_ix = transfer(TransferParams(
        from_pubkey=my_keypair.pubkey(),
        to_pubkey=registry_pubkey,
        lamports=0
    ))

    # 2. Create Memo Instruction
    memo_ix = Instruction(
        program_id=MEMO_PROGRAM_ID,
        accounts=[],
        data=manifest_json.encode('utf-8')
    )

    # Send transaction
    print("Publishing announcement to Solana...")
    try:
        # Get recent blockhash
        recent_blockhash = client.get_latest_blockhash().value.blockhash

        # Create message with BOTH instructions
        # Note: the order of accounts in Message matter.
        # But Message constructor from instructions usually handles it.
        msg = Message([transfer_ix, memo_ix], my_keypair.pubkey())
        txn = Transaction([my_keypair], msg, recent_blockhash)

        response = client.send_transaction(txn)
        print(f"Success! Transaction Hash: {response.value}")
    except Exception as e:
        print(f"Failed to send transaction: {e}")

if __name__ == "__main__":
    main()

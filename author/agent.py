import os
import json
import argparse
from typing import List, Optional
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solders.transaction import Transaction
from solders.message import Message
from solders.signature import Signature

# Load environment variables
load_dotenv(dotenv_path="author/.env")

class AgentManifest(BaseModel):
    agent_name: str
    niche: str
    tags: List[str]
    base_price_sol: float
    endpoint: str
    description: str

def get_keypair() -> Keypair:
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key_str:
        raise ValueError("SOLANA_PRIVATE_KEY not found in author/.env")
    key_data = json.loads(private_key_str)
    return Keypair.from_bytes(bytes(key_data))

def get_client() -> Client:
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    return Client(rpc_url)

def cmd_register(args):
    client = get_client()
    keypair = get_keypair()
    
    # Priority: CLI Args -> .env -> Defaults
    manifest = AgentManifest(
        agent_name=args.name or os.getenv("AGENT_NAME", "UnknownAgent"),
        niche=args.niche or os.getenv("AGENT_NICHE", "general"),
        tags=(args.tags or os.getenv("AGENT_TAGS", "")).split(","),
        base_price_sol=args.price if args.price is not None else float(os.getenv("AGENT_BASE_PRICE_SOL", 0.001)),
        endpoint=args.endpoint or os.getenv("AGENT_ENDPOINT", "http://localhost"),
        description=args.description or os.getenv("AGENT_DESCRIPTION", "")
    )
    
    manifest_json = manifest.model_dump_json()
    print(f"Publishing Manifest: {manifest_json}")

    MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
    memo_ix = Instruction(
        program_id=MEMO_PROGRAM_ID,
        accounts=[],
        data=manifest_json.encode('utf-8')
    )

    recent_blockhash = client.get_latest_blockhash().value.blockhash
    message = Message([memo_ix], keypair.pubkey())
    txn = Transaction([keypair], message, recent_blockhash)
    
    response = client.send_transaction(txn)
    print(f"Success! Transaction Hash: {response.value}")

def cmd_status(args):
    client = get_client()
    keypair = get_keypair()
    pubkey = keypair.pubkey()
    
    print(f"Agent Wallet: {pubkey}")
    
    # Balance
    res = client.get_balance(pubkey)
    print(f"Balance: {res.value / 1_000_000_000} SOL")
    
    # Last 5 Transactions
    print("\nLast 5 Transactions:")
    sig_resp = client.get_signatures_for_address(pubkey, limit=5)
    for sig_info in sig_resp.value:
        sig = str(sig_info.signature)
        # Try to parse memo if available
        memo = ""
        try:
            tx = client.get_transaction(Signature.from_string(sig), max_supported_transaction_version=0, encoding="jsonParsed")
            for ix in tx.value.transaction.transaction.message.instructions:
                ix_j = json.loads(ix.to_json())
                if ix_j.get('programId') == "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr":
                    memo = f" | Memo: {ix_j.get('parsed')[:50]}"
        except:
            pass
        print(f"- {sig[:16]}... | Slot: {sig_info.slot}{memo}")

def main():
    parser = argparse.ArgumentParser(description="Author Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Register/Update
    reg_parser = subparsers.add_parser("register", help="Register or update agent manifest")
    reg_parser.add_argument("--name", help="Agent name")
    reg_parser.add_argument("--niche", help="Agent niche")
    reg_parser.add_argument("--tags", help="Comma-separated tags")
    reg_parser.add_argument("--price", type=float, help="Base price in SOL")
    reg_parser.add_argument("--endpoint", help="API endpoint URL")
    reg_parser.add_argument("--description", help="Short description")

    # Status (Balance + History)
    subparsers.add_parser("status", help="Show wallet balance and recent transaction history")

    args = parser.parse_args()

    if args.command == "register":
        cmd_register(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

import os
import json
import argparse
import sys
from typing import List, Optional
from dotenv import load_dotenv

# Setup paths for importing from core/author
# Skills are executed from the project root or their own dir. 
# We'll try to find the project root.
script_dir = os.path.dirname(os.path.abspath(__file__))
# Relative to .gemini/skills/author-manager/scripts/
project_root = os.path.abspath(os.path.join(script_dir, "../../../../"))
sys.path.insert(0, project_root)

try:
    from core.models import AgentManifest
    from author.service import AgentRegistryService
except ImportError:
    # Fallback if executed from a different context
    print("Warning: Could not import core.models or author.service. Ensure project structure is correct.")
    # We'll define a local one as fallback or just fail
    raise

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.signature import Signature

# Load environment variables
load_dotenv(dotenv_path="author/.env")

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
    # Priority: CLI Args -> .env -> Defaults
    manifest = AgentManifest(
        agent_name=args.name or os.getenv("AGENT_NAME", "UnknownAgent"),
        niche=args.niche or os.getenv("AGENT_NICHE", "general"),
        tags=(args.tags or os.getenv("AGENT_TAGS", "")).split(","),
        base_price_usdc=args.price if args.price is not None else float(os.getenv("AGENT_BASE_PRICE_SOL", 0.001)),
        endpoint=args.endpoint or os.getenv("AGENT_ENDPOINT", "http://localhost"),
        description=args.description or os.getenv("AGENT_DESCRIPTION", "")
    )
    
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key_str:
        print("Error: SOLANA_PRIVATE_KEY not found.")
        return
    
    try:
        key_data = json.loads(private_key_str)
        rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
        service = AgentRegistryService(rpc_url, key_data)
        
        # Skill version might want to use the registry_pubkey from .env
        registry_pubkey = os.getenv("REGISTRY_PUBKEY")
        
        tx_hash = service.publish_manifest(manifest, registry_pubkey=registry_pubkey)
        if tx_hash:
            print(f"Success! Transaction Hash: {tx_hash}")
    except Exception as e:
        print(f"Failed to register agent: {e}")

def cmd_status(args):
    client = get_client()
    try:
        keypair = get_keypair()
    except Exception as e:
        print(f"Error loading keypair: {e}")
        return
        
    pubkey = keypair.pubkey()
    print(f"Agent Wallet: {pubkey}")
    
    # Balance
    try:
        res = client.get_balance(pubkey)
        print(f"Balance: {res.value / 1_000_000_000} SOL")
    except Exception as e:
        print(f"Error getting balance: {e}")
    
    # Last 5 Transactions
    print("\nLast 5 Transactions:")
    try:
        sig_resp = client.get_signatures_for_address(pubkey, limit=5)
        for sig_info in sig_resp.value:
            sig = str(sig_info.signature)
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
    except Exception as e:
        print(f"Error getting history: {e}")

def main():
    parser = argparse.ArgumentParser(description="Author Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Register/Update
    reg_parser = subparsers.add_parser("register", help="Register or update agent manifest")
    reg_parser.add_argument("--name", help="Agent name")
    reg_parser.add_argument("--niche", help="Agent niche")
    reg_parser.add_argument("--tags", help="Comma-separated tags")
    reg_parser.add_argument("--price", type=float, help="Base price")
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

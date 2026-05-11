import os
import json
import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, ValidationError
from dotenv import load_dotenv

from solana.rpc.api import Client
from solders.pubkey import Pubkey

# Load environment variables
load_dotenv()

# Setup paths for importing from core
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.models import AgentManifest

# Configuration from .env
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
REGISTRY_PUBKEY_STR = os.getenv("REGISTRY_PUBKEY")

if not REGISTRY_PUBKEY_STR:
    raise ValueError("REGISTRY_PUBKEY not found in .env file")

REGISTRY_PUBKEY = Pubkey.from_string(REGISTRY_PUBKEY_STR)

# 1. Connect to the network
client = Client(SOLANA_RPC_URL)

def find_data_providers_by_tag(target_tag: str, limit: int = 20) -> List[dict]:
    """
    Finds agents by tag. 
    NOTE: Scanning RPC logs is slow and doesn't scale. 
    TODO: Integrate with an indexer (Helius/Shyft) or a custom Program with PDA for O(1) discovery.
    """
    latest_providers = {}
    
    try:
        # 1. Get signatures (this is fast)
        sig_response = client.get_signatures_for_address(REGISTRY_PUBKEY, limit=limit)
    except Exception as e:
        print(f"Error fetching signatures: {e}")
        return []
    
    if not sig_response.value:
        return []

    # 2. Extract signatures for batch processing or sequential fetch
    # Optimization: Filter out transactions without memo if possible (not easy with standard getSignatures)
    
    for sig_info in sig_response.value:
        try:
            # Skip if we already have a more recent version of something and this is older 
            # (though we don't know the agent name yet, we can't fully optimize here without an indexer)
            
            tx = client.get_transaction(
                sig_info.signature, 
                max_supported_transaction_version=0,
                encoding="jsonParsed" # Use jsonParsed for easier memo extraction
            )
            
            if not tx.value or not tx.value.transaction:
                continue
                
            timestamp = tx.value.block_time
            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else "Unknown"

            # Search instructions for Memo
            instructions = tx.value.transaction.transaction.message.instructions
            for ix in instructions:
                # Standard Solana JSON parsing for Instructions
                ix_dict = json.loads(ix.to_json())
                program_id = ix_dict.get('programId')
                
                # Check for Memo Program
                if program_id == "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr":
                    memo_text = ix_dict.get('parsed')
                    if not memo_text: continue
                    
                    try:
                        # Validate using our shared core model
                        manifest = AgentManifest.model_validate_json(memo_text)
                        
                        if target_tag.lower() in [tag.lower() for tag in manifest.tags]:
                            name = manifest.agent_name
                            if name not in latest_providers or timestamp > latest_providers[name]['timestamp']:
                                latest_providers[name] = {
                                    "manifest": manifest,
                                    "timestamp": timestamp or 0,
                                    "date": date_str
                                }
                    except (ValidationError, json.JSONDecodeError):
                        continue
        except Exception as e:
            continue
    
    result = list(latest_providers.values())
    result.sort(key=lambda x: x['timestamp'], reverse=True)
    return result

if __name__ == "__main__":
    import sys
    
    # --- Running the Buyer Agent ---
    if len(sys.argv) > 1:
        tag_to_search = sys.argv[1]
    else:
        print("🤖 Solana Data Discovery Agent")
        print("===============================")
        tag_to_search = input("🔍 Enter tag to search (e.g., 'food', 'serbia', 'datasets'): ").strip()
    
    if not tag_to_search:
        if len(sys.argv) <= 1:
            print("❌ Search tag cannot be empty.")
    else:
        is_interactive = len(sys.argv) <= 1
        
        if is_interactive:
            print(f"\n🔎 Searching for agents with tag '{tag_to_search}'...")
        
        found_providers = find_data_providers_by_tag(tag_to_search)

        if not found_providers:
            print(f"📭 No agents found with tag '{tag_to_search}'.")
        else:
            if is_interactive:
                print(f"\n🎯 Found {len(found_providers)} matching providers (newest first):")
                print("=" * 60)
            
            for i, item in enumerate(found_providers, 1):
                agent = item['manifest']
                date = item['date']
                
                if is_interactive:
                    print(f"[{i}] {agent.agent_name.upper()} ({date})")
                    print(f"    💰 Price: {agent.base_price_usdc} USDC")
                    print(f"    🔗 Endpoint: {agent.endpoint}")
                    print(f"    📝 Description: {agent.description}")
                    print("-" * 60)
                else:
                    print(f"DATE: {date} | AGENT: {agent.agent_name} | PRICE: {agent.base_price_usdc} USDC | ENDPOINT: {agent.endpoint}")
            
            if is_interactive:
                print("\n💡 Now you can pick an endpoint to initiate data purchase.")

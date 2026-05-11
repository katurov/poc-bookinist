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
    # Temporary storage to keep track of the latest manifest per agent name
    latest_providers = {}
    
    # 2. Request the latest transactions for our registry address
    try:
        sig_response = client.get_signatures_for_address(REGISTRY_PUBKEY, limit=limit)
    except Exception as e:
        return []
    
    if not sig_response.value:
        return []

    # 3. Iterate through each transaction and extract details
    for sig_info in sig_response.value:
        try:
            tx = client.get_transaction(
                sig_info.signature, 
                max_supported_transaction_version=0
            )
            
            if not tx.value or not tx.value.transaction.meta:
                continue
                
            # Get block time (timestamp)
            timestamp = tx.value.block_time
            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S') if timestamp else "Unknown"

            logs = tx.value.transaction.meta.log_messages
            if not logs:
                continue
                
            for log in logs:
                if "Program log: Memo" in log:
                    try:
                        if "): " in log:
                            json_str = log.split('): ')[1]
                            if json_str.startswith('"') and json_str.endswith('"'):
                                try: json_str = json.loads(json_str)
                                except: pass
                        else: continue
                        
                        manifest = AgentManifest.model_validate_json(json_str)
                        
                        if target_tag.lower() in [tag.lower() for tag in manifest.tags]:
                            # Only keep the latest one for each unique agent name
                            name = manifest.agent_name
                            if name not in latest_providers or timestamp > latest_providers[name]['timestamp']:
                                latest_providers[name] = {
                                    "manifest": manifest,
                                    "timestamp": timestamp or 0,
                                    "date": date_str
                                }
                            
                    except (IndexError, ValidationError, json.JSONDecodeError):
                        continue
        except Exception as e:
            continue
    
    # Convert dict to list and sort by timestamp descending
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

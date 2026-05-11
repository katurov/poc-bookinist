import os
import json
import datetime
import sys
from typing import List, Optional
from pydantic import ValidationError

# Setup paths for importing from core
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../../../../"))
sys.path.insert(0, project_root)

try:
    from core.models import AgentManifest
except ImportError:
    print("Error: Could not import core.models. Ensure project structure is correct.")
    raise

try:
    from solana.rpc.api import Client
    from solders.pubkey import Pubkey
except ImportError:
    print("Error: Missing solana/solders packages. Install with 'pip install solana solders'")
    sys.exit(1)

# Default Registry (BalkanGastroNode registry)
DEFAULT_REGISTRY = "AUcZfbvuHswRZZy8nQybxZ6KezckoqNRqQCPVv17BrtD"
SOLANA_RPC_URL = "https://api.devnet.solana.com"

def find_experts(target_tag: str, registry_pubkey_str: str = DEFAULT_REGISTRY, limit: int = 15):
    client = Client(SOLANA_RPC_URL)
    registry_pubkey = Pubkey.from_string(registry_pubkey_str)
    
    try:
        sig_response = client.get_signatures_for_address(registry_pubkey, limit=limit)
    except Exception as e:
        return []
    
    if not sig_response.value:
        return []

    latest_providers = {}
    
    for sig_info in sig_response.value:
        try:
            # Using jsonParsed for efficiency as in client/discovery.py
            tx = client.get_transaction(
                sig_info.signature, 
                max_supported_transaction_version=0,
                encoding="jsonParsed"
            )
            if not tx.value or not tx.value.transaction:
                continue
                
            timestamp = tx.value.block_time
            instructions = tx.value.transaction.transaction.message.instructions
            
            for ix in instructions:
                ix_dict = json.loads(ix.to_json())
                if ix_dict.get('programId') == "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr":
                    memo_text = ix_dict.get('parsed')
                    if not memo_text: continue
                    
                    try:
                        # Use the shared core model for validation
                        manifest = AgentManifest.model_validate_json(memo_text)
                        
                        if target_tag.lower() in [tag.lower() for tag in manifest.tags] or target_tag.lower() in manifest.niche.lower():
                            name = manifest.agent_name
                            if name not in latest_providers or timestamp > latest_providers[name]['timestamp']:
                                latest_providers[name] = {
                                    "agent_name": manifest.agent_name,
                                    "niche": manifest.niche,
                                    "price_usdc": manifest.base_price_usdc,
                                    "endpoint": str(manifest.endpoint),
                                    "description": manifest.description,
                                    "timestamp": timestamp or 0
                                }
                    except (ValidationError, json.JSONDecodeError):
                        continue
        except Exception:
            continue
            
    result = list(latest_providers.values())
    result.sort(key=lambda x: x['timestamp'], reverse=True)
    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python discover_expert.py <topic>")
        sys.exit(1)
        
    topic = sys.argv[1]
    experts = find_experts(topic)
    
    if not experts:
        print(json.dumps({"status": "not_found", "topic": topic}))
    else:
        print(json.dumps({"status": "success", "experts": experts}, indent=2))

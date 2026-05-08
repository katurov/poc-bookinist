import os
import json
import datetime
import sys
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, ValidationError

try:
    from solana.rpc.api import Client
    from solders.pubkey import Pubkey
except ImportError:
    print("Error: Missing solana/solders packages. Install with 'pip install solana solders'")
    sys.exit(1)

# Default Registry (BalkanGastroNode registry)
DEFAULT_REGISTRY = "AUcZfbvuHswRZZy8nQybxZ6KezckoqNRqQCPVv17BrtD"
SOLANA_RPC_URL = "https://api.devnet.solana.com"

class AgentManifest(BaseModel):
    agent_name: str
    niche: str
    tags: List[str]
    base_price_sol: Optional[float] = 0.01
    endpoint: str
    description: str

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
            tx = client.get_transaction(sig_info.signature, max_supported_transaction_version=0)
            if not tx.value or not tx.value.transaction.meta:
                continue
                
            timestamp = tx.value.block_time
            logs = tx.value.transaction.meta.log_messages or []
            
            for log in logs:
                if "Program log: Memo" in log:
                    try:
                        if "): " in log:
                            json_str = log.split('): ')[1]
                        else: continue
                        
                        # Handle potential double encoding
                        if json_str.startswith('"') and json_str.endswith('"'):
                            try: json_str = json.loads(json_str)
                            except: pass
                        
                        data = json.loads(json_str)
                        manifest = AgentManifest(**data)
                        
                        if target_tag.lower() in [tag.lower() for tag in manifest.tags] or target_tag.lower() in manifest.niche.lower():
                            name = manifest.agent_name
                            if name not in latest_providers or timestamp > latest_providers[name]['timestamp']:
                                latest_providers[name] = {
                                    "agent_name": manifest.agent_name,
                                    "niche": manifest.niche,
                                    "price_sol": manifest.base_price_sol,
                                    "endpoint": manifest.endpoint,
                                    "description": manifest.description,
                                    "timestamp": timestamp or 0
                                }
                    except:
                        continue
        except:
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

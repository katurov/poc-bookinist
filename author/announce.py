import os
import json
import sys
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import HttpUrl
from dotenv import load_dotenv

# Setup paths for importing from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import AgentManifest
from author.service import AgentRegistryService

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

def get_key_data_from_string(key_str: str) -> list:
    try:
        key_data = json.loads(key_str)
        if isinstance(key_data, list):
            return key_data
    except json.JSONDecodeError:
        pass
    raise ValueError("Private key format not recognized. Please use a JSON array of bytes.")

def main():
    try:
        settings = AppSettings()
    except Exception as e:
        print(f"Error loading settings: {e}")
        return
        
    # Prepare Manifest
    manifest = AgentManifest(
        agent_name=settings.agent_name,
        niche=settings.agent_niche,
        tags=[t.strip() for t in settings.agent_tags.split(",")],
        base_price_usdc=settings.agent_base_price_usdc,
        endpoint=settings.agent_endpoint,
        description=settings.agent_description
    )
    
    try:
        key_data = get_key_data_from_string(settings.solana_private_key)
    except Exception as e:
        print(f"Error loading keypair data: {e}")
        return

    print("Publishing announcement to Solana...")
    try:
        service = AgentRegistryService(settings.solana_rpc_url, key_data)
        tx_hash = service.publish_manifest(manifest, registry_pubkey=settings.registry_pubkey)
        if tx_hash:
            print(f"Success! Transaction Hash: {tx_hash}")
    except Exception as e:
        print(f"Failed to send transaction: {e}")

if __name__ == "__main__":
    main()

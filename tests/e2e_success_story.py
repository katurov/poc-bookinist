import os
import sys
import json
import time
import asyncio
import subprocess
import httpx
from dotenv import load_dotenv

# Setup paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import AgentManifest
from author.service import AgentRegistryService
from client.discovery import find_data_providers_by_tag
from client.fetch_data import fetch_data

# Load .env
load_dotenv(dotenv_path="author/.env")

async def test_announcement_and_discovery():
    print("\n--- Phase 1: Announcement & Discovery ---")
    
    # 1. Setup Manifest
    agent_name = f"TestAgent_{int(time.time())}"
    tag = "e2e_test_tag"
    manifest = AgentManifest(
        agent_name=agent_name,
        niche="testing",
        tags=[tag, "automated"],
        base_price_usdc=0.001,
        endpoint="http://localhost:3333/v1/",
        description="Automated E2E Test Agent"
    )

    # 2. Publish Announcement
    print(f"Publishing announcement for {agent_name}...")
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    key_data = json.loads(private_key_str)
    
    service = AgentRegistryService(rpc_url, key_data)
    tx_hash = service.publish_manifest(manifest, registry_pubkey=os.getenv("REGISTRY_PUBKEY"))
    
    if not tx_hash:
        print("❌ Failed to publish announcement.")
        return False
    print(f"✅ Announcement published! TX: {tx_hash}")

    # 3. Wait for propagation
    print("Waiting 15 seconds for Solana propagation...")
    await asyncio.sleep(15)

    # 4. Discover via Client
    print(f"Searching for agent with tag: {tag}...")
    providers = find_data_providers_by_tag(tag, limit=10)
    
    found = any(p['manifest'].agent_name == agent_name for p in providers)
    if found:
        print(f"✅ Success! Agent {agent_name} found in registry.")
        return True
    else:
        print("❌ Agent not found in registry (might need more time).")
        return False

async def test_server_and_deal():
    print("\n--- Phase 2: Server & Deal ---")
    
    # 1. Start Server
    print("Starting server...")
    server_process = subprocess.Popen(
        [sys.executable, "bookinist/server_main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to be ready
    print("Waiting for server to start...")
    ready = False
    for _ in range(10):
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get("http://localhost:3333/v1/")
                if res.status_code == 200:
                    ready = True
                    break
        except:
            pass
        await asyncio.sleep(2)
    
    if not ready:
        print("❌ Server failed to start.")
        server_process.terminate()
        return False
    
    print("✅ Server is UP.")

    # 2. Conduct Deal via Client
    print("Initiating fetch_data with automated payment...")
    try:
        # We wrap the existing fetch_data logic
        # This will trigger 402, pay, and then get data
        await fetch_data("http://localhost:3333/v1/", "burger")
        print("✅ Deal successful! Data received from protected endpoint.")
        result = True
    except Exception as e:
        print(f"❌ Deal failed: {e}")
        result = False
    finally:
        print("Stopping server...")
        server_process.terminate()
        
    return result

async def main():
    print("🚀 Starting E2E Success Story Test")
    
    # Phase 1
    announcement_ok = await test_announcement_and_discovery()
    
    # Phase 2 (independent start, but logic follows)
    deal_ok = await test_server_and_deal()
    
    print("\n" + "="*40)
    if announcement_ok and deal_ok:
        print("🎉 E2E TEST PASSED: Full lifecycle verified.")
    else:
        print("⚠️  E2E TEST FAILED: Check logs above.")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(main())

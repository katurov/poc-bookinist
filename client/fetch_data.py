import os
import json
import sys
import asyncio
import httpx
import base64
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

from solders.keypair import Keypair
from x402 import x402Client, parse_payment_required
try:
    from client.schemes import NativeSolSvmScheme
except ImportError:
    from schemes import NativeSolSvmScheme

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, ".env")
load_dotenv(env_path)

# Configuration from .env
PRIVATE_KEY_STR = os.getenv("CLIENT_PRIVATE_KEY")
if not PRIVATE_KEY_STR:
    print("❌ ERROR: CLIENT_PRIVATE_KEY not found in .env")
    sys.exit(1)

try:
    key_data = json.loads(PRIVATE_KEY_STR)
    CLIENT_KEYPAIR = Keypair.from_bytes(bytes(key_data))
except Exception as e:
    print(f"❌ ERROR parsing CLIENT_PRIVATE_KEY: {e}")
    sys.exit(1)

# Initialize x402 client
class SignerWrapper:
    def __init__(self, keypair):
        self._keypair = keypair
    
    @property
    def address(self) -> str:
        return str(self._keypair.pubkey())
    
    @property
    def keypair(self) -> Keypair:
        return self._keypair

x402_client = x402Client()
# Use our custom scheme that handles Native SOL cleanly
x402_client.register("solana:*", NativeSolSvmScheme(SignerWrapper(CLIENT_KEYPAIR)))

async def fetch_data(base_url, query, signature_payload=None, depth=0):
    """
    Fetches data from an x402-enabled provider using automated payment handling.
    """
    if depth > 1:
        print("🛑 Maximum payment attempts reached. Stopping to prevent loop.")
        return

    headers = {}
    if signature_payload:
        headers["payment-signature"] = signature_payload
        print(f"🔑 Retrying with x402 payment payload...")

    print(f"🔗 Connecting to provider at: {base_url}")
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        try:
            # 1. Get manifest
            manifest_res = await http_client.get(base_url)
            manifest_res.raise_for_status()
            manifest_json = manifest_res.json()
            
            usage = manifest_json.get("usage", {})
            endpoint = usage.get("endpoint")
            method = usage.get("method", "POST")
            
            if not endpoint:
                print("❌ ERROR: Manifest missing endpoint.")
                return

            parsed_base = urlparse(base_url)
            domain_root = f"{parsed_base.scheme}://{parsed_base.netloc}"
            full_url = urljoin(domain_root, endpoint)
            
            # 2. Data request
            if method == "POST":
                payload = {"query": query, "limit": 3}
                res = await http_client.post(full_url, json=payload, headers=headers)
            else:
                params = {"query": query}
                res = await http_client.get(full_url, params=params, headers=headers)
                
            # 3. Handle 402 Payment Required
            if res.status_code == 402:
                if signature_payload:
                    print("❌ Payment payload was rejected by server.")
                    return

                print("🛑 HTTP 402: Payment Required!")
                pay_req_header = res.headers.get("payment-required") or res.headers.get("Payment-Required")
                
                if not pay_req_header:
                    print("❌ Missing 'payment-required' header.")
                    return

                try:
                    pr_data = base64.b64decode(pay_req_header)
                    payment_required = parse_payment_required(pr_data)
                    
                    print("✍️  Generating x402 payment payload...")
                    payload = await x402_client.create_payment_payload(payment_required)
                    
                    # If payload is already a dict (from our custom scheme), we need to handle it.
                    # But x402Client usually wraps it in a model.
                    if hasattr(payload, "model_dump_json"):
                        payload_json = payload.model_dump_json()
                    else:
                        payload_json = json.dumps(payload)
                        
                    payload_base64 = base64.b64encode(payload_json.encode()).decode()
                    
                    return await fetch_data(base_url, query, signature_payload=payload_base64, depth=depth+1)
                except Exception as e:
                    print(f"❌ x402 Payment process failed: {e}")
                    return
            
            res.raise_for_status()
            results = res.json()
            
            print(f"\n✅ Data Received:")
            print("=" * 60)
            items = results if isinstance(results, list) else results.get("results", [])
            for i, item in enumerate(items, 1):
                name = item.get('name') or item.get('title') or "Unknown Item"
                print(f"[{i}] {name}")
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "burger"
    target_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3333/v1/"
    if not target_url.endswith('/'): target_url += '/'
    asyncio.run(fetch_data(target_url, query))

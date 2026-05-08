import os
import json
from solana.rpc.api import Client
from solders.keypair import Keypair
from dotenv import load_dotenv

# Load environment variables from the specific .env file in the client folder
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

def main():
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    client = Client(rpc_url)
    
    private_key_str = os.getenv("CLIENT_PRIVATE_KEY")
    if not private_key_str:
        print("Error: CLIENT_PRIVATE_KEY not found in client/.env")
        return
        
    try:
        key_data = json.loads(private_key_str)
        my_keypair = Keypair.from_bytes(bytes(key_data))
    except Exception as e:
        print(f"Error parsing private key: {e}")
        return

    pubkey = my_keypair.pubkey()
    print(f"Fetching recent transactions for: {pubkey}\n")
    
    try:
        response = client.get_signatures_for_address(pubkey, limit=5)
        signatures = response.value
        
        if not signatures:
            print("No transactions found for this address.")
            return

        for sig_info in signatures:
            sig = str(sig_info.signature)
            print(f"Signature: {sig}")
            print(f"Slot: {sig_info.slot}")
            print(f"Memo/Status: {sig_info.memo or 'N/A'}")
            print("-" * 20)

    except Exception as e:
        print(f"Failed to fetch transactions: {e}")

if __name__ == "__main__":
    main()

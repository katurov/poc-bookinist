import os
import json
from solana.rpc.api import Client
from solders.keypair import Keypair
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="author/.env")

def main():
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    client = Client(rpc_url)
    
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key_str:
        print("Error: SOLANA_PRIVATE_KEY not found in author/.env")
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
        # Get transaction signatures for the public key
        response = client.get_signatures_for_address(pubkey, limit=10)
        signatures = response.value
        
        if not signatures:
            print("No transactions found for this address.")
            return

        print(f"{'#':<3} {'Signature':<88} {'Slot':<10}")
        print("-" * 105)
        
        for i, sig_info in enumerate(signatures, 1):
            sig = str(sig_info.signature)
            slot = sig_info.slot
            print(f"{i:<3} {sig:<88} {slot:<10}")
            print(f"    View: https://explorer.solana.com/tx/{sig}?cluster=devnet\n")

    except Exception as e:
        print(f"Failed to fetch transactions: {e}")

if __name__ == "__main__":
    main()

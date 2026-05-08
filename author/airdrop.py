import os
import json
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from dotenv import load_dotenv

load_dotenv()

def main():
    rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com")
    client = Client(rpc_url)
    
    private_key_str = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key_str:
        print("Error: SOLANA_PRIVATE_KEY not found in .env")
        return
        
    try:
        key_data = json.loads(private_key_str)
        my_keypair = Keypair.from_bytes(bytes(key_data))
    except Exception as e:
        print(f"Error parsing private key: {e}")
        return

    pubkey = my_keypair.pubkey()
    print(f"Requesting airdrop for {pubkey} on devnet...")
    
    try:
        # Airdrop 1 SOL
        res = client.request_airdrop(pubkey, 1_000_000_000)
        print(f"Airdrop requested. Signature: {res.value}")
        print("Wait a few seconds for the transaction to finalize, then run announce.py")
    except Exception as e:
        print(f"Airdrop failed: {e}")
        print("You can also use: https://faucet.solana.com/")

if __name__ == "__main__":
    main()

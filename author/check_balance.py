import os
import json
from solana.rpc.api import Client
from solders.keypair import Keypair
from dotenv import load_dotenv

# Load environment variables from the specific .env file in the author folder
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
    print(f"Checking balance for: {pubkey}")
    
    try:
        response = client.get_balance(pubkey)
        balance_lamports = response.value
        balance_sol = balance_lamports / 1_000_000_000
        print(f"Balance: {balance_sol} SOL")
        
        if balance_sol == 0:
            print("\nYour balance is 0. Please use author/airdrop.py or visit https://faucet.solana.com/")
    except Exception as e:
        print(f"Failed to fetch balance: {e}")

if __name__ == "__main__":
    main()

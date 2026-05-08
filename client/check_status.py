import os
import json
import asyncio
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from spl.token.instructions import get_associated_token_address
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
        from solders.keypair import Keypair
        my_keypair = Keypair.from_bytes(bytes(key_data))
    except Exception as e:
        print(f"Error parsing private key: {e}")
        return

    pubkey = my_keypair.pubkey()
    print(f"Checking status for: {pubkey}")
    
    # Check SOL
    try:
        sol_balance = client.get_balance(pubkey).value
        print(f"SOL Balance: {sol_balance / 1e9} SOL")
    except Exception as e:
        print(f"Failed to fetch SOL balance: {e}")

    # Check USDC ATA status
    usdc_mint = Pubkey.from_string("4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
    ata = get_associated_token_address(pubkey, usdc_mint)
    print(f"USDC ATA: {ata}")
    
    try:
        token_balance = client.get_token_account_balance(ata)
        if token_balance.value:
            print(f"USDC Balance: {token_balance.value.ui_amount}")
        else:
            print("USDC Balance: 0 (Account exists but empty)")
    except Exception as e:
        if "matched no account" in str(e):
            print("USDC ATA does not exist yet.")
        else:
            print(f"Failed to fetch USDC balance: {e}")

if __name__ == "__main__":
    main()

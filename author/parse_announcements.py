import os
import json
from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.signature import Signature
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
    print(f"Reading announcements for: {pubkey}\n")
    
    try:
        # Get transaction signatures
        sig_resp = client.get_signatures_for_address(pubkey, limit=10)
        signatures = sig_resp.value
        
        if not signatures:
            print("No transactions found.")
            return

        print(f"{'Slot':<10} | {'Price':<7} | {'Manifest content'}")
        print("-" * 100)

        for sig_info in signatures:
            sig_str = str(sig_info.signature)
            # Use jsonParsed encoding to get readable memo data
            tx_resp = client.get_transaction(
                Signature.from_string(sig_str), 
                max_supported_transaction_version=0, 
                encoding="jsonParsed"
            )
            
            if tx_resp.value is None:
                continue

            memo_data = "N/A"
            price = "N/A"
            
            try:
                # In jsonParsed, we can find the memo text easily
                transaction = tx_resp.value.transaction
                instructions = transaction.transaction.message.instructions
                
                for ix in instructions:
                    # Search for Memo Program
                    ix_json = json.loads(ix.to_json())
                    if ix_json.get('programId') == "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr":
                        memo_text = ix_json.get('parsed')
                        if memo_text:
                            memo_data = memo_text
                            try:
                                manifest = json.loads(memo_text)
                                price = f"{manifest.get('base_price_usdc', 'N/A')}"
                            except:
                                pass
            except Exception as e:
                pass

            if memo_data != "N/A":
                print(f"{sig_info.slot:<10} | {price:<7} | {memo_data[:75]}...")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

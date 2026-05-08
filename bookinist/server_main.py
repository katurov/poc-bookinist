import os
import uvicorn
from fastapi import FastAPI, Body
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from restaurant_search import RestaurantSearch

# x402 imports
from x402 import x402ResourceServer, FacilitatorConfig
from x402.http import HTTPFacilitatorClient, x402HTTPResourceServer
from x402.mechanisms.svm.exact import ExactSvmServerScheme
from x402.http.middleware.fastapi import PaymentMiddlewareASGI

# Load environment variables
load_dotenv()

app = FastAPI(title="Bookinist Restaurant Agent API")

# --- x402 Setup ---
FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL", "https://x402.org/facilitator")
RECIPIENT_ADDRESS = "FhGVcaiZvBd7zQaifuNnAYUe69MiktFMjwJxVa38L2jT" 
NETWORK_ID = "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1" # V2 Devnet
PRICE_USD = "0.01"

# 1. Local Facilitator for SOL support
from x402.schemas import VerifyResponse, SettleResponse, SupportedResponse, SupportedKind
from x402.mechanisms.svm.utils import decode_transaction_from_payload, extract_transaction_info
from x402.mechanisms.svm.types import ExactSvmPayload

class LocalSvmFacilitator:
    def __init__(self, rpc_url="https://api.devnet.solana.com"):
        from solana.rpc.api import Client
        self.client = Client(rpc_url)

    async def verify(self, payload, requirements):
        print(f"DEBUG LOCAL FACILITATOR: Verifying {requirements.asset}...")
        try:
            # Parse payload
            svm_payload = ExactSvmPayload.from_dict(payload.payload)
            tx = decode_transaction_from_payload(svm_payload)
            
            # Check for native SOL transfer
            if str(requirements.asset) == "11111111111111111111111111111111":
                # Manual verification of system transfer
                msg = tx.message
                static_accounts = list(msg.account_keys)
                for ix in msg.instructions:
                    program = static_accounts[ix.program_id_index]
                    if str(program) == "11111111111111111111111111111111":
                        # Found system program
                        data = bytes(ix.data)
                        if len(data) >= 12 and data[0] == 2: # Transfer
                            amount = int.from_bytes(data[4:12], "little")
                            if amount >= int(requirements.amount):
                                # Verify destination
                                dest = static_accounts[ix.accounts[1]]
                                if str(dest) == str(requirements.pay_to):
                                    payer = str(static_accounts[ix.accounts[0]])
                                    print(f"DEBUG LOCAL FACILITATOR: SOL Transfer verified! Payer: {payer}")
                                    return VerifyResponse(is_valid=True, payer=payer)
                
                return VerifyResponse(is_valid=False, invalid_reason="no_sol_transfer_found", payer="")
            
            # For other assets, we don't handle them here (or we could)
            return VerifyResponse(is_valid=False, invalid_reason="unsupported_asset", payer="")
        except Exception as e:
            print(f"DEBUG LOCAL FACILITATOR: Error during verify: {e}")
            return VerifyResponse(is_valid=False, invalid_reason=str(e), payer="")

    async def settle(self, payload, requirements):
        print(f"DEBUG LOCAL FACILITATOR: Settling {requirements.asset}...")
        try:
            svm_payload = ExactSvmPayload.from_dict(payload.payload)
            # Send transaction to network
            from solders.transaction import VersionedTransaction
            import base64
            tx_bytes = base64.b64decode(svm_payload.transaction)
            # Note: For real settlement we'd need to sign it if it's partially signed,
            # but here the client should have provided a fully signed transaction 
            # if they are paying their own fees.
            # However, x402 expects the facilitator to sign as fee payer.
            # For this hack, let's assume the client pays fees.
            
            res = self.client.send_raw_transaction(tx_bytes)
            sig = str(res.value)
            print(f"DEBUG LOCAL FACILITATOR: Settlement success! Signature: {sig}")
            return SettleResponse(success=True, transaction=sig, network=str(requirements.network), payer="")
        except Exception as e:
            print(f"DEBUG LOCAL FACILITATOR: Error during settle: {e}")
            return SettleResponse(success=False, error_reason=str(e), transaction="", network=str(requirements.network), payer="")

    def get_supported(self):
        return SupportedResponse(kinds=[
            SupportedKind(x402_version=2, scheme="exact", network=NETWORK_ID, extra={"feePayer": RECIPIENT_ADDRESS})
        ])

# 2. Initialize local facilitator
facilitator = LocalSvmFacilitator()

# 3. Create core x402 resource server
core_server = x402ResourceServer(facilitator)

# 4. Register SVM (Solana) scheme on core server
core_server.register(NETWORK_ID, ExactSvmServerScheme())

# 5. Configure protected routes (Requesting SOL explicitly)
routes = {
    "POST /v1/search": {
        "accepts": [
            {
                "scheme": "exact",
                "network": NETWORK_ID,
                "pay_to": RECIPIENT_ADDRESS,
                "price": {
                    "amount": "10000000",  # 0.01 SOL in lamports
                    "asset": "11111111111111111111111111111111"  # Native SOL
                }
            }
        ]
    }
}

# 6. Add Middleware
app.add_middleware(PaymentMiddlewareASGI, server=core_server, routes=routes)
# --- End x402 Setup ---

# Initialize our search library
search_engine = RestaurantSearch()

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class RestaurantResponse(BaseModel):
    name: str
    gault_millau_review: str
    phone: str
    address: str
    website: str
    rerank_score: float

@app.get("/v1/")
async def get_manifest():
    """
    Returns the manual/manifest for the Gemini agent.
    """
    return {
        "description": "API для поиска ресторанов в Нови-Саде с использованием Gault&Millau обзоров и NVIDIA reranking. Этот эндпоинт ПЛАТНЫЙ ($0.01 за запрос).",
        "usage": {
            "endpoint": "/v1/search",
            "method": "POST",
            "parameters": {
                "query": "Строка запроса (например, 'лучшие бургеры' или 'уютное кафе')",
                "limit": "Количество результатов (по умолчанию 5)"
            },
            "payment": {
                "required": True,
                "price": f"${PRICE_USD}",
                "network": NETWORK_ID,
                "address": RECIPIENT_ADDRESS
            },
            "response": "Список объектов ресторанов с подробной информацией и скором релевантности (rerank_score)."
        },
        "system_prompt_hint": "Используй этот инструмент, когда пользователь спрашивает рекомендации ресторанов в Нови-Саде. Твой ответ должен основываться на предоставленных обзорах. Предупреди пользователя, что запрос платный."
    }

@app.post("/v1/search", response_model=List[RestaurantResponse])
async def search_restaurants(request: SearchRequest):
    """
    Performs search and returns JSON results.
    """
    results = search_engine.search(request.query, rerank_limit=request.limit)
    return results

@app.on_event("shutdown")
def shutdown_event():
    search_engine.close()

if __name__ == "__main__":
    PORT = 3333
    print(f"Starting x402-protected server on http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

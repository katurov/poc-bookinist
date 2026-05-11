import os
import sys
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv

# Setup paths for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bookinist.middlewares.facilitator import LocalSvmFacilitator
from bookinist.routers.v1 import router as v1_router

# x402 imports
from x402 import x402ResourceServer
from x402.mechanisms.svm.exact import ExactSvmServerScheme
from x402.http.middleware.fastapi import PaymentMiddlewareASGI

# Load environment variables
load_dotenv()

app = FastAPI(title="Bookinist Restaurant Agent API")

# --- x402 Configuration ---
RECIPIENT_ADDRESS = os.getenv("RECIPIENT_ADDRESS", "FhGVcaiZvBd7zQaifuNnAYUe69MiktFMjwJxVa38L2jT")
NETWORK_ID = os.getenv("NETWORK_ID", "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1")
SOL_PRICE_LAMPORTS = os.getenv("SOL_PRICE_LAMPORTS", "10000000") # 0.01 SOL

# 1. Initialize local facilitator
facilitator = LocalSvmFacilitator(network_id=NETWORK_ID, recipient_address=RECIPIENT_ADDRESS)

# 2. Create core x402 resource server
core_server = x402ResourceServer(facilitator)

# 3. Register SVM (Solana) scheme on core server
core_server.register(NETWORK_ID, ExactSvmServerScheme())

# 4. Configure protected routes
protected_routes = {
    "POST /v1/search": {
        "accepts": [
            {
                "scheme": "exact",
                "network": NETWORK_ID,
                "pay_to": RECIPIENT_ADDRESS,
                "price": {
                    "amount": SOL_PRICE_LAMPORTS,
                    "asset": "11111111111111111111111111111111"  # Native SOL
                }
            }
        ]
    }
}

# 5. Add Middleware
app.add_middleware(PaymentMiddlewareASGI, server=core_server, routes=protected_routes)

# Include Routers
app.include_router(v1_router)

if __name__ == "__main__":
    PORT = int(os.getenv("PORT", 3333))
    print(f"Starting x402-protected server on http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)

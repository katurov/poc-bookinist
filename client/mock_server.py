from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

# In-memory "database" of verified signatures (for demo purposes)
# In reality, the server would check the blockchain
verified_signatures = set()

@app.get("/v1/")
async def get_manifest():
    return {
        "description": "MOCK API for testing x402 payments.",
        "usage": {
            "endpoint": "/v1/search",
            "method": "POST"
        }
    }

@app.post("/v1/search")
async def search_restaurants(request: Request, x_payment_signature: str = Header(None)):
    if not x_payment_signature:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "payment": {
                    "amount_sol": 0.001,
                    "recipient": "GBKnT17gh9wHF6KhjR3qgWjy31emer7i9CaEooW2YSCe", # Using client's own pubkey for demo safety
                    "instructions": "Pay 0.001 SOL to access this premium data."
                }
            }
        )
    
    # Simulating verification
    print(f"📡 Mock Server: Received payment signature: {x_payment_signature}")
    return [
        {
            "name": "Mock Healthy Garden",
            "address": "123 Green St",
            "rerank_score": 0.95,
            "gault_millau_review": "Excellent organic food found in this mock response."
        }
    ]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3334)

# Bookinist: AI Restaurant Guide for Novi Sad (x402 Enabled)

Bookinist is a specialized AI agent tool designed to help users find the best dining experiences in Novi Sad. It leverages high-quality restaurant reviews from **Gault\u0026Millau**, utilizes **Weaviate** for vector search, and applies **NVIDIA NIM Reranking** for maximum relevance. The service is monetized using the **x402** protocol on the **Solana Devnet**.

## 🚀 Key Features
- **Semantic Search**: Understands natural language queries (e.g., "romantic dinner near the park").
- **NVIDIA Reranking**: Uses the `rerank-qa-mistral-4b` model to ensure the most relevant results are ranked highest.
- **x402 Monetization**: Integrated Pay-per-Query logic using Solana Devnet.
- **Gemini Agent Integration**: Provides a structured manifest for AI agents to use as a tool.

## 📂 Project Structure
- `server_main.py`: The main FastAPI server. Handles the agent manifest and the x402-protected search endpoint.
- `restaurant_search.py`: The core search library. Performs hybrid search in Weaviate and manual reranking via NVIDIA API.
- `setup_weaviate.py`: Utility script to initialize the Weaviate collection and load processed data.
- `analyze_restos.py`: Data enrichment script that used GPT-4o to extract structured info from Gault\u0026Millau reviews.
- `download_md.py`: Scraper that converted restaurant web pages to clean Markdown via `markdown.new`.
- `restaurants_data.pkl`: The project's "database" - a DataFrame containing all enriched restaurant information.
- `.env`: Contains API keys for OpenAI, NVIDIA, and configuration for x402.

## 🛠 Technology Stack
- **Backend**: FastAPI (Python 3.10+)
- **Vector DB**: Weaviate (Local Docker)
- **Embeddings**: OpenAI `text-embedding-3-small`
- **Reranker**: NVIDIA NIM `rerank-qa-mistral-4b`
- **Payments**: x402 Protocol
- **Blockchain**: Solana (Devnet)

## 💰 Monetization \u0026 Verification (For Judges)

The system implements the **HTTP 402 Payment Required** standard. Every search request costs **$0.01**.

### Payment Details:
- **Network**: Solana Devnet (`solana:103`)
- **Seller Address**: `FhGVcaiZvBd7zQaifuNnAYUe69MiktFMjwJxVa38L2jT`
- **Currency**: USDC (or native SOL equivalent depending on facilitator setup)

### How to Verify:
1.  **Direct Request**: Try to call `POST http://localhost:3333/v1/search` with any JSON body.
2.  **Expected Response**: The server will return `402 Payment Required` with a header/body containing payment instructions.
3.  **Transaction Check**: Once a payment is made, the transaction can be verified on the [Solana Explorer (Devnet)](https://explorer.solana.com/?cluster=devnet) by searching for the Seller Address: `FhGVcaiZvBd7zQaifuNnAYUe69MiktFMjwJxVa38L2jT`.
4.  **x402 Proof**: The client provides a `payment-proof` header. The server validates this proof with the **x402 Facilitator** before processing the AI search.

## 📖 Setup \u0026 Run
1.  **Start Weaviate**: Ensure Weaviate is running in Docker with `text2vec-openai` and `reranker-nvidia` modules enabled.
2.  **Install Deps**: `pip install fastapi uvicorn weaviate-client requests python-dotenv x402 pandas`
3.  **Load Data**: `python3 setup_weaviate.py`
4.  **Run Server**: `python3 server_main.py`
5.  **Access Manifest**: Open `http://localhost:3333/v1/` to see the agent manual.

---
*Created for the x402 Hackathon. Exploring the future of agentic payments.*

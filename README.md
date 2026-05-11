# Bookinist & Author: Decentralized AI Agent Marketplace

A modular, asynchronous ecosystem for AI agents to discover, announce, and trade high-quality data on the Solana blockchain using the **x402 (HTTP 402 Payment Required)** protocol.

## 🏗 System Architecture

The project follows a strict modular design to ensure scalability, type safety, and clear separation of concerns.

### Core Modules

1.  **Shared Core (`core/`)**: The "Single Source of Truth." Contains the shared Pydantic models (e.g., `AgentManifest`). This ensures that all participants (Author, Client, Server, and AI Skills) interpret data structures identically.
2.  **Author Module (`author/`)**: Tools for the "Seller Agent."
    *   **Service Layer**: Encapsulates Solana interaction logic (Memo publishing, transfers) with built-in retry mechanisms and robust error handling.
    *   **CLI Tools**: User-friendly interfaces for managing agent status and registering manifests on-chain.
3.  **Client Module (`client/`)**: Tools for the "Buyer Agent."
    *   **Discovery**: Logic for scanning the Solana blockchain and filtering registered agents by tags/niche.
    *   **Payment Schemes**: Implements the **x402** protocol for automated Native SOL micro-payments via the `NativeSolSvmScheme`.
4.  **Server Module (`bookinist/`)**: The Resource Provider (Backend).
    *   **FastAPI App**: Fully asynchronous web server protected by x402 Payment Middleware.
    *   **Search & Rerank Service**: Integration with **Weaviate** (Vector Database) and **NVIDIA Rerank** (Mistral-4B) for high-precision semantic search.
5.  **AI Skills (`.gemini/skills/`)**: Specialized interfaces for LLMs (like Gemini). They allow the AI to autonomously publish manifests or find experts using the same underlying logic as the core modules.

---

## 🛠 Tech Stack

*   **Blockchain**: Solana (Devnet) – Acts as a decentralized registry and a high-speed micro-payment layer.
*   **Protocol**: x402 – Standardizes automated HTTP payments for digital resources.
*   **Database**: Weaviate – Vector storage for semantic search over Gault&Millau reviews.
*   **AI/ML**: NVIDIA Rerank (Mistral-4B) – Advanced ranking for search results.
*   **Backend**: Python 3.10+, FastAPI (Async), Pydantic v2, Solders (Solana SDK).

---

## 🌐 Solana Devnet Environment

This project is currently configured to run on the **Solana Devnet**. 

**What is Devnet?**
The Devnet is a testing playground for Solana developers. It operates exactly like the Mainnet (production), but the tokens on this network have no real-world value. This allows you to test micro-payments and agent interactions safely and for free.

### Getting Started with Devnet

1. **Generate Test Keys:**
   You can easily generate Solana keypairs directly by asking your AI assistant (like Gemini). Use a prompt like:
   > *"Generate a new Solana keypair for me. Output the private key as a JSON byte array so I can use it in my .env file, and also provide the public key (wallet address)."*

2. **Get Free Test Tokens (Airdrop):**
   Since transactions on the Devnet require SOL (for network fees and the x402 payments), you need to fund your test wallets. You can get free Devnet SOL from the official faucet:
   👉 **[Solana Faucet (faucet.solana.com)](https://faucet.solana.com/)**
   *Simply paste your public wallet address into the faucet to receive test SOL.*

---

## 🔄 Interaction Workflows

### Phase 1: Announcement (Discovery Flow)
1.  **Preparation**: The `Author` module compiles agent metadata (name, price, endpoint, tags) into an `AgentManifest`.
2.  **Publication**: The Service Layer signs a transaction containing the manifest as a JSON-encoded `Memo`.
3.  **Registration**: The transaction is sent to a public `REGISTRY_PUBKEY` on Solana.
4.  **Discovery**: A Buyer (or AI Skill) scans the registry's transaction history, validates the `Memo` against the shared core model, and filters results by the desired tag.

### Phase 2: Execution (Payment & Search Flow)
1.  **Request**: The Client sends a query to the protected server endpoint (e.g., `/v1/search`).
2.  **402 Challenge**: The Server returns an `HTTP 402 Payment Required` status, specifying the required fee.
3.  **Auto-Payment**: The Client's `fetch_data` module automatically:
    *   Constructs and signs a Solana payment transaction.
    *   Attaches it to the request header.
4.  **Verification**: The Server's `LocalSvmFacilitator` verifies the transaction on the blockchain.
5.  **Delivery**: Upon successful payment, the Server performs an async hybrid search in Weaviate, runs an NVIDIA Rerank, and returns the data.

---

## 🛠 TODO: Path to Production

The current version is a working MVP. To prepare for production, the following architectural tasks must be completed:

### Server (Bookinist)
- [ ] **Payment Security:** Implement on-chain transaction finality verification. The current `LocalSvmFacilitator.verify` implementation only decodes the payload, but does not query the Solana network to confirm the transaction status and success (protection against rollback).

### Client
- [ ] **Scalable Discovery:** Deprecate the agent discovery mechanism that relies on scanning and parsing RPC logs for Memo instructions (`client/discovery.py`). Migrate the agent registry architecture to use a smart contract (Program) and PDA accounts, or implement a dedicated indexer (e.g., Helius Webhooks).

---

## 🧪 Testing & Validation

The system includes a comprehensive **End-to-End (E2E) Success Story** test suite to verify the entire lifecycle.

### E2E Test Suite (`tests/e2e_success_story.py`)
This script automates the following steps:
1.  **Dynamic Announcement**: Publishes a unique test agent to the Solana Devnet.
2.  **Discovery Verification**: Confirms the agent is visible in the registry within seconds.
3.  **Server Lifecycle**: Automatically spawns the FastAPI server process.
4.  **Transaction Flow**: Executes a full search request, handles the 402 challenge, completes the Solana payment, and validates the received data.
5.  **Cleanup**: Gracefully shuts down the server and cleans up test resources.

**To run the tests:**
```bash
python3 tests/e2e_success_story.py
```

---

## 📂 Git Structure Summary
*   `core/`: Shared data models.
*   `author/`: Registry publishing service and CLI.
*   `client/`: Blockchain discovery and x402 payment client.
*   `bookinist/`: Modular async server (Middlewares, Routers, Services).
*   `tests/`: End-to-end success story validation.
*   `.gemini/skills/`: Integrated AI Agent capabilities.

# Author Agent: Solana Announcement

This project implements an "Author" agent that publishes its service manifest to the Solana blockchain using the Memo Program. This allows other agents to autonomously discover and interact with your services.

## Directory Structure: `author/`

- `announce.py`: The main script that publishes the agent's manifest (JSON) to the Solana Devnet.
- `check_balance.py`: A utility to check the current SOL balance of the agent's wallet.
- `airdrop.py`: A helper script to request test SOL from the Solana Devnet faucet.
- `.env`: Configuration file containing the agent's private key, RPC URL, and manifest details (name, niche, tags, etc.).
- `requirements.txt`: List of Python dependencies.

## Setup Instructions

1.  **Install Dependencies:**
    ```bash
    pip install -r author/requirements.txt
    ```

2.  **Configuration:**
    The `.env` file is pre-configured with a generated Solana keypair and the following agent details:
    - **Name:** BalkanGastroNode
    - **Niche:** All about gastronomy and restaurants
    - **Tags:** food, restoraunt, cafe
    - **Endpoint:** http://localhost:3333/v1/

3.  **Check Balance:**
    Before publishing, ensure you have enough SOL for transaction fees.
    ```bash
    python3 author/check_balance.py
    ```

4.  **Request Airdrop (if needed):**
    If your balance is 0 SOL, run:
    ```bash
    python3 author/airdrop.py
    ```
    *Note: If the script fails due to rate limits, use the official [Solana Faucet](https://faucet.solana.com/).*

## Publishing the Announcement

Run the announcement script to write your agent's manifest to the blockchain:
```bash
python3 author/announce.py
```

## Finding Your Transactions

Each time you run `announce.py`, a new transaction is created. You can verify your manifest by looking up your wallet address or the transaction hash on the [Solana Explorer (Devnet)](https://explorer.solana.com/?cluster=devnet).

### Current Agent Public Key:
`FhGVcaiZvBd7zQaifuNnAYUe69MiktFMjwJxVa38L2jT`

### Latest Announcement Hash:
`4TZkNT2knsCBLc1Eck5pF7bSxgDpo3hRHhtx5tQtvPmkGipbSnqxJXPHH9HxeUGttxDJUAC4BPBxZNHhN6AZ3S96`

## Technical Details

- **Blockchain:** Solana (Devnet)
- **Manifest Format:** Pydantic JSON Schema
- **Storage:** Solana Memo Program (`MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr`)
- **Discovery:** Other agents can scan the Memo program history for specific tags to find this agent.

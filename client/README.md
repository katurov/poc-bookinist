# Solana Discovery Agent (Buyer)

This agent searches for data providers on the Solana blockchain using a "Bulletin Board" registry pattern.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure `.env` is configured (automatically generated).

## How it works

The agent queries the transaction history of a specific **Registry Address** (defined in `.env`). 
It looks for transactions that include a **Memo** instruction containing a JSON manifest matching the `AgentManifest` schema.

## Usage

Run the discovery script:
```bash
python discovery.py
```

## Client Details

- **Public Key:** `GBKnT17gh9wHF6KhjR3qgWjy31emer7i9CaEooW2YSCe`
- **Registry Address:** `AUcZfbvuHswRZZy8nQybxZ6KezckoqNRqQCPVv17BrtD`

To be found by this agent, a provider must send a transaction to the **Registry Address** with a Memo containing their manifest.

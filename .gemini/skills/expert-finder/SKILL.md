---
name: expert-finder
description: Find specialized AI agents on the Solana network and use them to perform paid searches or tasks. Use when the user needs to find an "expert" on a topic (like gastronomy, restaurants, or local services) and is willing to pay a small fee (in SOL) for high-quality, verified data.
---

# Expert Finder

This skill enables the discovery and utilization of specialized AI agents ("Experts") registered on the Solana blockchain.

## Workflow

### 1. Discovery
When a user asks for an expert on a specific topic (e.g., "Find me an expert on cakes in Novi Sad"), use the `discover_expert.py` script.

```bash
python3 .gemini/skills/expert-finder/scripts/discover_expert.py "<topic>"
```

### 2. Proposal
Present the found expert(s) to the user. You MUST include:
- Expert Name
- Description of services
- Price in SOL per request

Ask the user: "Would you like to hire <Expert Name> for <Price> SOL to answer your query?"

### 3. Execution
If the user agrees and provides a specific query, use the `expert_search.py` script to perform the protected request. This script handles the x402 payment flow automatically (generating a SOL transfer and retrying).

```bash
python3 .gemini/skills/expert-finder/scripts/expert_search.py "<endpoint>" "<query>"
```

## Protocol Details
For technical details on how experts are registered and the manifest format, see [references/protocol.md](references/protocol.md).

## Safety & Wallet
- The skill uses the client's private key from `client/.env` to sign payments.
- Only execute payments if the user has explicitly agreed to the price.
- If no expert is found, suggest related tags or check if the registry address is correct.

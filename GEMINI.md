# Project Context and Instructions for Gemini Agent

This file contains project-specific instructions to help the Gemini agent assist users effectively within the Bookinist & Author MVP workspace.

## 1. Environment and Network
* **Network:** The project strictly operates on the **Solana Devnet**.
* **Currency:** All transactions, fees, and prices are in Devnet SOL (which has no real monetary value).
* **x402 Protocol:** The project uses the x402 standard for automated HTTP micro-payments.

## 2. Assisting Users with Testing Setup
When a user wants to run or test the project, they will need Solana keypairs and test tokens. Proactively offer to help them set this up.

### Generating Keys
If the user needs keys for the `.env` files (`author/.env`, `client/.env`, `bookinist/.env`), you can generate them using a Python script in the background or provide them directly. 
**Format requirement:** The private key must be a JSON array of integers (e.g., `[12, 34, 255, ...]`), which is the format expected by the `solders` library.
*Example prompt you can fulfill:* "Generate a Solana keypair for my client/.env file."

### Getting Test Tokens (Airdrop)
If the user runs into "insufficient funds" errors or asks how to pay for transactions:
1. Explain that this is the Devnet and they need free test SOL.
2. Instruct them to visit the official faucet: **https://faucet.solana.com/**
3. Tell them to copy their public key (wallet address) and paste it into the faucet to receive tokens.
4. Alternatively, you can use the `solana airdrop` command via CLI if the Solana tool suite is installed locally.

## 3. Managing Skills
The project includes specialized agent skills in the `.gemini/skills/` directory.
If the user asks about connecting or using skills (like `author-manager` or `expert-finder`):
1. Explain that skills are localized expert agents that enhance Gemini's capabilities.
2. Instruct the user that they can activate these skills within their Gemini CLI environment.
3. As an agent, you can call `activate_skill(name="<skill_name>")` when you identify that the user is trying to perform a task related to a specific skill (e.g., registering an author agent or searching for an expert).
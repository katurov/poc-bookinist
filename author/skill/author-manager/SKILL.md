---
name: author-manager
description: Manage the "Author" agent on Solana. Use this skill to register the agent (assets, endpoint, price) or check wallet status/balance when the user mentions registering assets, endpoints, or checking agent status.
---

# Author Manager Skill

This skill allows Gemini to manage an "Author" agent that publishes its manifest to the Solana blockchain.

## Workflow: Registering Assets / Endpoint

When the user says "I want to register my assets" or similar:

1.  **Gather Information**: Ask the user for the following details (if not already known or in `.env`):
    - **Agent Name**: The public name of the agent.
    - **Description**: A short manifest describing what the agent does.
    - **Tags**: Keywords for discovery (comma-separated).
    - **Endpoint URL**: The HTTP address where the agent's API is hosted.
    - **Price**: The base price per request in SOL (e.g., 0.001).

2.  **Validation**: Confirm the details with the user before publishing.

3.  **Execution**: Use the bundled `agent.py` script to publish the registration.
    ```bash
    python3 scripts/agent.py register --name "<NAME>" --description "<DESC>" --tags "<TAGS>" --endpoint "<URL>" --price <PRICE>
    ```

## Workflow: Checking Status

When the user wants to check the agent's wallet or transaction history:

1.  **Execution**: Use the `status` command.
    ```bash
    python3 scripts/agent.py status
    ```

## Resources

- `scripts/agent.py`: Unified CLI for Solana interactions.
- `scripts/.env`: Configuration for RPC and private keys.

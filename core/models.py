from typing import List, Union
from pydantic import BaseModel, HttpUrl

class AgentManifest(BaseModel):
    agent_name: str
    niche: str
    tags: List[str]
    # Accommodate both base_price_sol and base_price_usdc just in case during transition,
    # or just use base_price_usdc as it's more prevalent.
    # We will use base_price_usdc as the primary, but allow base_price_sol for backward compatibility in the network?
    # Let's align on base_price_usdc and endpoint as HttpUrl to match client.
    base_price_usdc: float = 0.0
    endpoint: Union[HttpUrl, str]
    description: str

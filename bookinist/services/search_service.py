import weaviate
import weaviate.classes.query as wvq
import os
import httpx
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

class RestaurantSearch:
    def __init__(self):
        # Weaviate v4 connect_to_local is actually synchronous for setup, 
        # but queries can be async if using the async client.
        # However, for simplicity and to match recommendations, we'll use httpx for NVIDIA 
        # and we can keep Weaviate as is or use its async features.
        # Let's use the async client for Weaviate if possible.
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        self.nvidia_api_url = "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"
        
        self.client = weaviate.use_async_with_local(
            headers={
                "X-OpenAI-Api-Key": self.api_key
            }
        )

    async def _get_rerank_scores(self, query: str, passages: List[str]) -> List[float]:
        """
        Fetches relevance scores from NVIDIA API using async httpx client.
        """
        if not passages:
            return []

        headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": "nvidia/rerank-qa-mistral-4b",
            "query": {"text": query},
            "passages": [{"text": p} for p in passages],
            "truncate": "NONE"
        }

        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(self.nvidia_api_url, headers=headers, json=payload)
            if response.status_code != 200:
                print(f"NVIDIA API Error {response.status_code}: {response.text}")
                return [0.0] * len(passages)
            
            rankings = response.json().get("rankings", [])
            # Sort by original index to match input order
            sorted_rankings = sorted(rankings, key=lambda x: x["index"])
            return [item["logit"] for item in sorted_rankings]

    async def search(self, query_text: str, limit: int = 10, rerank_limit: int = 5) -> List[Dict[str, Any]]:
        """
        Performs hybrid search in Weaviate (async), then async NVIDIA Rerank.
        """
        async with self.client as client:
            collection = client.collections.get("Restaurant")
            
            # 1. Hybrid Search in Weaviate
            response = await collection.query.hybrid(
                query=query_text,
                limit=limit,
                return_metadata=wvq.MetadataQuery(score=True)
            )
            
            if not response.objects:
                return []

            # 2. Extract content for Reranking
            objects = response.objects
            passages = [obj.properties.get("gault_millau_review", "") for obj in objects]
            
            # 3. Get Rerank Scores (Async)
            rerank_scores = await self._get_rerank_scores(query_text, passages)
            
            # 4. Combine and Sort
            results = []
            for i, obj in enumerate(objects):
                res = dict(obj.properties)
                res['weaviate_score'] = obj.metadata.score
                res['rerank_score'] = rerank_scores[i] if i < len(rerank_scores) else 0.0
                results.append(res)
                
            # Sort by rerank score descending
            results.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            return results[:rerank_limit]

    async def close(self):
        # The 'async with' handles closing, but we keep this for compatibility
        pass

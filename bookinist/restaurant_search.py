import weaviate
import weaviate.classes.query as wvq
import os
import requests
from dotenv import load_dotenv

load_dotenv()

class RestaurantSearch:
    def __init__(self):
        self.client = weaviate.connect_to_local(
            headers={
                "X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")
            }
        )
        self.collection = self.client.collections.get("Restaurant")
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        self.nvidia_api_url = "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"

    def _get_rerank_scores(self, query, passages):
        """
        Fetches relevance scores from NVIDIA API using the format from HowToRerank.md
        """
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

        response = requests.post(self.nvidia_api_url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"NVIDIA API Error {response.status_code}: {response.text}")
            return [0.0] * len(passages)
        
        rankings = response.json().get("rankings", [])
        # Sort by original index to match input order
        sorted_rankings = sorted(rankings, key=lambda x: x["index"])
        return [item["logit"] for item in sorted_rankings]

    def search(self, query_text, limit=10, rerank_limit=5):
        """
        Performs hybrid search in Weaviate, then manual NVIDIA Rerank on top results.
        """
        # 1. Hybrid Search in Weaviate
        response = self.collection.query.hybrid(
            query=query_text,
            limit=limit,
            return_metadata=wvq.MetadataQuery(score=True)
        )
        
        if not response.objects:
            return []

        # 2. Extract content for Reranking
        objects = response.objects
        passages = [obj.properties.get("gault_millau_review", "") for obj in objects]
        
        # 3. Get Rerank Scores
        rerank_scores = self._get_rerank_scores(query_text, passages)
        
        # 4. Combine and Sort
        results = []
        for i, obj in enumerate(objects):
            res = dict(obj.properties)
            res['weaviate_score'] = obj.metadata.score
            res['rerank_score'] = rerank_scores[i]
            results.append(res)
            
        # Sort by rerank score descending
        results.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return results[:rerank_limit]

    def close(self):
        self.client.close()

# Test script
if __name__ == "__main__":
    searcher = RestaurantSearch()
    
    test_queries = [
        "Best burgers in Novi Sad",
        "Fine dining with a French influence",
        "Healthy sweets and gluten free cakes"
    ]
    
    for q in test_queries:
        print(f"\n>>> Query: '{q}'")
        results = searcher.search(q, rerank_limit=3)
        for i, res in enumerate(results, 1):
            print(f"  {i}. {res['name']}")
            print(f"     Rerank Score: {res['rerank_score']:.4f}")
            print(f"     Address: {res['address']}")
            
    searcher.close()

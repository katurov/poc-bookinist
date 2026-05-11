from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import List, Optional
from bookinist.services.search_service import RestaurantSearch

router = APIRouter(prefix="/v1")
search_engine = RestaurantSearch()

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class RestaurantResponse(BaseModel):
    name: str
    gault_millau_review: str
    phone: str
    address: str
    website: str
    rerank_score: float

@router.get("/")
async def get_manifest():
    """
    Returns the manual/manifest for the Gemini agent.
    """
    # These constants should ideally be passed from a config
    NETWORK_ID = "solana:EtWTRABZaYq6iMfeYKouRu166VU2xqa1"
    RECIPIENT_ADDRESS = "FhGVcaiZvBd7zQaifuNnAYUe69MiktFMjwJxVa38L2jT"
    
    return {
        "description": "API для поиска ресторанов в Нови-Саде с использованием Gault&Millau обзоров и NVIDIA reranking. Этот эндпоинт ПЛАТНЫЙ ($0.01 за запрос).",
        "usage": {
            "endpoint": "/v1/search",
            "method": "POST",
            "parameters": {
                "query": "Строка запроса (например, 'лучшие бургеры' или 'уютное кафе')",
                "limit": "Количество результатов (по умолчанию 5)"
            },
            "payment": {
                "required": True,
                "price": "$0.01",
                "network": NETWORK_ID,
                "address": RECIPIENT_ADDRESS
            },
            "response": "Список объектов ресторанов с подробной информацией и скором релевантности (rerank_score)."
        },
        "system_prompt_hint": "Используй этот инструмент, когда пользователь спрашивает рекомендации ресторанов в Нови-Саде. Твой ответ должен основываться на предоставленных обзорах. Предупреди пользователя, что запрос платный."
    }

@router.post("/search", response_model=List[RestaurantResponse])
async def search_restaurants(request: SearchRequest):
    """
    Performs search and returns JSON results.
    """
    results = await search_engine.search(request.query, rerank_limit=request.limit)
    return results

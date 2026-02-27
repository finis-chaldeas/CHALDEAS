"""
SHEBA Chat API — HistoryAgent 기반 대화 인터페이스.

프로덕션 엔드포인트: POST /chat/agent
이전 Orchestrator 기반 엔드포인트(/chat, /chat/observe, /chat/rag)는
HistoryAgent로 통합되어 제거됨.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

router = APIRouter()


# ============================================================
# Agent API - Intelligent Query Processing
# ============================================================

class AgentRequest(BaseModel):
    """Request for agent-based intelligent processing."""
    query: str = Field(..., description="User query in any language")
    api_key: Optional[str] = Field(None, description="User's OpenAI API key (required)")
    language: str = Field("en", description="Response language: en, ko, ja")


class StructuredDataModel(BaseModel):
    """Structured data in response."""
    type: str
    items: Optional[List[Dict[str, Any]]] = None
    events: Optional[List[Dict[str, Any]]] = None
    chain: Optional[List[Dict[str, Any]]] = None
    markers: Optional[List[Dict[str, Any]]] = None
    cards: Optional[List[Dict[str, Any]]] = None
    comparison_axes: Optional[List[str]] = None


class AgentAnalysis(BaseModel):
    """Query analysis result."""
    original_query: str
    english_query: str
    intent: str
    intent_confidence: str
    entities: Dict[str, Any]
    response_format: str
    search_strategy: str
    requires_multiple_searches: bool


class AgentSearchResult(BaseModel):
    """Single search result."""
    query_used: str
    filters_applied: Dict[str, Any]
    results: List[Dict[str, Any]]
    result_count: int


class AgentResponseData(BaseModel):
    """Agent response data."""
    intent: str
    format: str
    answer: str
    structured_data: Dict[str, Any]
    sources: List[Dict[str, Any]]
    confidence: float
    suggested_followups: List[str]


class AgentResponse(BaseModel):
    """Full agent response including analysis and results."""
    analysis: AgentAnalysis
    search_results: List[AgentSearchResult]
    response: AgentResponseData


@router.post("/agent", response_model=AgentResponse)
async def agent_chat(request: AgentRequest):
    """
    Intelligent agent-based chat endpoint.

    - LOCAL DEV: Uses server's OPENAI_API_KEY env var if available
    - PRODUCTION: Requires user's own API key
    - NO KEY: Falls back to BM25 keyword search (free, limited)

    This endpoint uses the HistoryAgent which:
    1. Analyzes the query intent (comparison, timeline, causation, etc.)
    2. Extracts entities (events, persons, locations, time periods)
    3. Plans and executes appropriate searches
    4. Generates structured responses based on intent
    5. Enhances sources with attribution (integrated from LAPLACE)
    6. Adjusts confidence via verification (integrated from PAPERMOON)
    7. Generates contextual follow-up suggestions

    Example:
        POST /api/v1/chat/agent
        {"query": "마라톤 전투", "api_key": "sk-..."}  # Full AI
        {"query": "마라톤 전투"}  # BM25 fallback or local dev with env var
    """
    # Determine which API key to use
    api_key = request.api_key

    # In development, fallback to server's env var if no user key provided
    if not api_key:
        is_dev = os.getenv("CHALDEAS_ENV", "development") == "development"
        server_key = os.getenv("OPENAI_API_KEY")

        if is_dev and server_key:
            # Local development: use server's key
            api_key = server_key
            print("[SHEBA] Using server API key (development mode)")

    # If still no API key, use BM25 search fallback
    if not api_key:
        try:
            from app.services.hybrid_search import HybridSearchService

            bm25_service = HybridSearchService.get_instance()
            results = bm25_service.basic_search(request.query, limit=10)

            # Format BM25 results as agent response
            sources = [
                {"id": r["id"], "title": r["title"], "similarity": r["score"]}
                for r in results[:5]
            ]

            # Build simple answer from results
            if results:
                answer = f"'{request.query}' 검색 결과 {len(results)}건을 찾았습니다. AI 분석을 원하시면 OpenAI API 키를 입력해주세요."
            else:
                answer = f"'{request.query}'에 대한 검색 결과가 없습니다."

            return AgentResponse(
                analysis=AgentAnalysis(
                    original_query=request.query,
                    english_query=request.query,
                    intent="search",
                    intent_confidence="low",
                    entities={"keywords": [request.query]},
                    response_format="cards",
                    search_strategy="bm25_fallback",
                    requires_multiple_searches=False
                ),
                search_results=[AgentSearchResult(
                    query_used=request.query,
                    filters_applied={},
                    results=[{"content_type": "event", "content_id": r["id"], "content_text": r["title"], "metadata": r, "similarity": r["score"]} for r in results],
                    result_count=len(results)
                )],
                response=AgentResponseData(
                    intent="search",
                    format="cards",
                    answer=answer,
                    structured_data={"type": "cards", "cards": [{"title": r["title"], "content": r.get("description", "")[:200] if r.get("description") else "", "subtitle": f"{abs(r.get('date_start', 0))} {'BCE' if r.get('date_start', 0) < 0 else 'CE'}"} for r in results[:5]]},
                    sources=sources,
                    confidence=0.5,
                    suggested_followups=[]
                )
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"BM25 search failed: {str(e)}")

    # Validate API key format
    if not api_key.startswith("sk-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format. OpenAI API keys start with 'sk-'."
        )

    try:
        # Create a new agent instance with the determined API key
        from app.core.sheba.history_agent import HistoryAgent
        from app.services.rag_service import RAGService

        # Create RAG service with key
        user_rag_service = RAGService(api_key=api_key)

        # Create agent with key
        user_agent = HistoryAgent(
            rag_service=user_rag_service,
            api_key=api_key
        )

        result = user_agent.process(request.query, language=request.language)

        return AgentResponse(
            analysis=AgentAnalysis(**result["analysis"]),
            search_results=[AgentSearchResult(**sr) for sr in result["search_results"]],
            response=AgentResponseData(**result["response"])
        )
    except Exception as e:
        # Check for API key errors
        error_str = str(e).lower()
        if "api key" in error_str or "authentication" in error_str or "unauthorized" in error_str:
            raise HTTPException(
                status_code=401,
                detail="Invalid OpenAI API key. Please check your API key and try again."
            )
        raise HTTPException(status_code=500, detail=str(e))

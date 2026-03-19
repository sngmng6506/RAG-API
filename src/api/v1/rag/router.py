from fastapi import APIRouter, HTTPException

from src.core.config import settings
from src.services.rag_service import retrieve, generate

from .schemas import (
    RetrieveRequest, RetrieveResponse,
    QueryRequest, QueryResponse,
    ChunkResult,
)

router = APIRouter(prefix="/v1/rag", tags=["rag"])


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_endpoint(req: RetrieveRequest):
    """질문 → 임베딩 → Chroma 검색 → 청크 반환 (use_parent=True이면 부모 텍스트)."""
    collection = req.collection_name or settings.CHROMA_COLLECTION_NAME
    try:
        chunks = retrieve(collection, req.question, top_k=req.top_k, use_parent=req.use_parent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return RetrieveResponse(
        question=req.question,
        chunks=[ChunkResult(**c) for c in chunks],
    )


@router.post("/query", response_model=QueryResponse)
def query_endpoint(req: QueryRequest):
    """질문 → 검색 → LLM(gpt-oss-20b) 답변 생성 (use_parent=True이면 부모 텍스트를 context로)."""
    collection = req.collection_name or settings.CHROMA_COLLECTION_NAME
    try:
        chunks = retrieve(collection, req.question, top_k=req.top_k, use_parent=req.use_parent)
        answer = generate(req.question, chunks, temperature=req.temperature, max_tokens=req.max_tokens)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return QueryResponse(
        question=req.question,
        answer=answer,
        chunks=[ChunkResult(**c) for c in chunks],
    )

"""RAG 서비스: Retrieval + Generation."""
from __future__ import annotations

import httpx

from src.core.config import settings
from src.prompts import render
from src.services.embed_service import embed_texts
from src.services.ingest_service import (
    get_chroma_client,
    get_collection,
    _load_parents,
)


def retrieve(
    collection_name: str,
    question: str,
    top_k: int | None = None,
    use_parent: bool = False,
) -> list[dict]:
    """
    질문을 임베딩 후 Chroma에서 유사한 자식 청크 검색.

    use_parent=False: 자식 청크 텍스트 그대로 반환.
    use_parent=True : 자식으로 검색하되, parent_chunk_id로 부모 텍스트를 조회해 교체.
                      같은 부모에 여러 자식이 히트해도 부모 한 번만 포함 (best score 유지).

    반환: [{"text": str, "source": str, "page": int, "score": float}, ...]
    """
    k = top_k or settings.RAG_TOP_K
    query_embedding = embed_texts([question])[0]

    client = get_chroma_client()
    coll = get_collection(client, collection_name)  # 컬렉션 없으면 ValueError 발생

    results = coll.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    # 자식 청크 목록 구성
    children = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        children.append({
            "text": doc,
            "source": meta.get("source", ""),
            "page": meta.get("page", 0),
            "score": round(1 - dist, 4),
            "parent_chunk_id": meta.get("parent_chunk_id", ""),
        })

    if not use_parent:
        # parent_chunk_id는 내부 필드이므로 제거 후 반환
        return [{k: v for k, v in c.items() if k != "parent_chunk_id"} for c in children]

    # use_parent=True: 부모 텍스트로 교체 (부모 중복 제거, best score 유지)
    parent_store = _load_parents(collection_name)
    seen: dict[str, dict] = {}  # parent_chunk_id → chunk dict

    for child in children:
        pid = child["parent_chunk_id"]
        parent = parent_store.get(pid)
        if parent is None:
            # 부모를 찾지 못하면 자식 텍스트 그대로 사용
            entry = {
                "text": child["text"],
                "source": child["source"],
                "page": child["page"],
                "score": child["score"],
            }
            key = child["text"]  # 자식 텍스트를 중복 제거 키로
        else:
            entry = {
                "text": parent["text"],
                "source": parent["source"],
                "page": parent["page"],
                "score": child["score"],
            }
            key = pid

        # 같은 부모가 여러 자식에 히트하면 score가 높은 것 유지
        if key not in seen or child["score"] > seen[key]["score"]:
            seen[key] = entry

    return list(seen.values())


def generate(
    question: str,
    chunks: list[dict],
    temperature: float = 0.1,
    max_tokens: int | None = None,
) -> str:
    """
    검색된 청크를 context로 LLM(gpt-oss-20b)에 전달해 답변 생성.
    vLLM OpenAI-compatible API 사용.
    """
    context = "\n\n".join(
        f"[출처: {c['source']} p.{c['page']}]\n{c['text']}" for c in chunks
    )
    prompt = render("rag_prompt", context=context, question=question)

    url = f"http://{settings.VLLM_LLM_HOST}:{settings.VLLM_LLM_PORT}/v1/chat/completions"
    payload = {
        "model": settings.VLLM_LLM_SERVED_MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens or settings.RAG_MAX_TOKENS,
    }

    with httpx.Client(timeout=120.0, verify=False) as client:
        resp = client.post(url, json=payload)
        if not resp.is_success:
            raise RuntimeError(f"LLM 호출 실패 {resp.status_code}: {resp.text}")

    message = resp.json()["choices"][0]["message"]

    # reasoning 모델: content(최종 답변) 우선, 없으면 RuntimeError
    # reasoning_content는 내부 추론 과정이므로 사용하지 않음
    answer = message.get("content")
    if not answer:
        raise RuntimeError("LLM이 최종 답변(content)을 생성하지 못했습니다. max_tokens를 늘려주세요.")
    return answer.strip()

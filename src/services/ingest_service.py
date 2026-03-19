"""
Chroma: 자식 청크만 임베딩 저장 (벡터 검색 대상).
부모 저장소: 컬렉션당 파일 하나 ({PARENT_STORE_DIR}/{collection_name}.json)
  - 구조: { chunk_id: {"text", "source", "page"}, ... }

"""
from __future__ import annotations

import json
from pathlib import Path

import chromadb

from src.core.config import settings
from src.services.document_service import parse_file
from src.services.embed_service import embed_texts


def _parent_file(collection_name: str) -> Path:
    path = Path(settings.PARENT_STORE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{collection_name}.json"


def _load_parents(collection_name: str) -> dict:
    filepath = _parent_file(collection_name)
    if not filepath.exists():
        return {}
    return json.loads(filepath.read_text(encoding="utf-8"))


def _save_parents(collection_name: str, data: dict) -> None:
    _parent_file(collection_name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_parent(collection_name: str, chunk_id: str) -> dict | None:
    """parent_chunk_id로 부모 청크 조회."""
    return _load_parents(collection_name).get(chunk_id)


def get_chroma_client() -> chromadb.HttpClient:
    return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT, ssl=False)


def list_collections() -> list[str]:
    client = get_chroma_client()
    return [c.name for c in client.list_collections()]


def get_or_create_collection(client: chromadb.HttpClient, name: str):
    return client.get_or_create_collection(name=name, embedding_function=None)


def get_collection(client: chromadb.HttpClient, name: str):
    """컬렉션이 없으면 ValueError 발생."""
    try:
        return client.get_collection(name=name, embedding_function=None)
    except Exception:
        raise ValueError(f"컬렉션 '{name}'을 찾을 수 없습니다.")


def upload(
    collection_name: str,
    file_content: bytes,
    filename: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> dict:
    """
    파일 → 파싱 → 저장 (Hierarchical Chunking).
    - 부모: {collection_name}.json 에 chunk_id 키로 누적 저장.
    - 자식: TEI 임베딩 → Chroma 저장.
    """
    result = parse_file(
        file_content,
        filename,
        chunk_size=chunk_size or settings.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
    )
    parents = result["parents"]
    children = result["children"]

    if not parents and not children:
        return {"parents_added": 0, "children_added": 0}

    # 부모 → 컬렉션 JSON 파일에 누적 저장
    parent_store = _load_parents(collection_name)
    for p in parents:
        parent_store[p["chunk_id"]] = {
            "text": p["text"],
            "source": p["source"],
            "page": p["page"],
        }
    _save_parents(collection_name, parent_store)

    # 자식 → TEI 임베딩 후 Chroma 저장
    if children:
        child_texts = [c["text"] for c in children]
        child_embeddings = embed_texts(child_texts)

        client = get_chroma_client()
        coll = get_or_create_collection(client, collection_name)

        coll.add(
            ids=[c["chunk_id"] for c in children],
            embeddings=child_embeddings,
            documents=child_texts,
            metadatas=[{
                "source": c["source"],
                "page": c["page"],
                "chunk_index": c["chunk_index"],
                "parent_chunk_id": c["parent_chunk_id"],
                "chunk_id": c["chunk_id"],
            } for c in children],
        )

    return {"parents_added": len(parents), "children_added": len(children)}


def list_files(collection_name: str) -> list[str]:
    """컬렉션 내 파일명(source) 목록 반환."""
    client = get_chroma_client()
    coll = get_collection(client, collection_name)
    result = coll.get(include=["metadatas"])
    sources = {m["source"] for m in result["metadatas"] if m.get("source")}
    return sorted(sources)


def delete_file(collection_name: str, file_name: str) -> dict:
    """
    특정 파일(source)에 해당하는 청크를 Chroma와 부모 JSON에서 모두 삭제.
    반환: {"children_deleted": int, "parents_deleted": int}
    """
    client = get_chroma_client()
    coll = get_collection(client, collection_name)

    # 해당 source의 자식 청크 ID 조회
    result = coll.get(where={"source": file_name}, include=["metadatas"])
    child_ids = result["ids"]

    if not child_ids:
        raise ValueError(f"'{file_name}' 파일을 컬렉션 '{collection_name}'에서 찾을 수 없습니다.")

    # 연결된 parent_chunk_id 수집
    parent_ids = {m["parent_chunk_id"] for m in result["metadatas"] if m.get("parent_chunk_id")}

    # Chroma에서 자식 청크 삭제
    coll.delete(ids=child_ids)

    # 부모 JSON에서 해당 파일의 부모 청크 삭제
    parent_store = _load_parents(collection_name)
    before = len(parent_store)
    for pid in parent_ids:
        parent_store.pop(pid, None)
    _save_parents(collection_name, parent_store)
    parents_deleted = before - len(parent_store)

    return {"children_deleted": len(child_ids), "parents_deleted": parents_deleted}


def delete_collection(collection_name: str) -> dict:
    """Chroma 컬렉션 전체 삭제 + 부모 JSON 파일 삭제."""
    client = get_chroma_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        raise ValueError(f"컬렉션 '{collection_name}'을 찾을 수 없습니다.")

    # 부모 JSON 파일도 삭제
    filepath = _parent_file(collection_name)
    if filepath.exists():
        filepath.unlink()

    return {"deleted": collection_name}
"""문서 파싱: PDF → 큰 청크(페이지, 부모) + 작은 청크(고정 크기, 자식)."""
from __future__ import annotations

import io
import uuid
from typing import Any

from pypdf import PdfReader

from src.core.config import settings


def parse_file(
    content: bytes,
    filename: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    반환:
        {
            "parents": [{"chunk_id", "text", "page", "source"}, ...],
            "children": [{"chunk_id", "parent_chunk_id", "text", "page",
                          "chunk_index", "source"}, ...],
        }
    chunk_size / chunk_overlap: None이면 config 기본값 사용.
    """
    if not filename.lower().endswith(".pdf"):
        raise ValueError(f"PDF만 지원합니다. 전달된 파일: {filename}")

    c_size = chunk_size or settings.CHUNK_SIZE
    c_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    reader = PdfReader(io.BytesIO(content))
    parents = []
    children = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue

        parent_id = str(uuid.uuid4())
        parents.append({
            "chunk_id": parent_id,
            "text": page_text,
            "page": page_num,
            "source": filename,
        })

        chunks = _split_by_size(
            page_text,
            chunk_size=c_size,
            overlap=c_overlap,
        )
        for idx, chunk_text in enumerate(chunks):
            children.append({
                "chunk_id": str(uuid.uuid4()),
                "parent_chunk_id": parent_id,
                "text": chunk_text,
                "page": page_num,
                "chunk_index": idx,
                "source": filename,
            })

    return {"parents": parents, "children": children}


def _split_by_size(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    텍스트를 chunk_size 글자 단위로 자르고, overlap 만큼 겹침.
    예) chunk_size=500, overlap=50 → 0~500, 450~950, 900~1400, ...
    """
    if not text:
        return []

    chunks = []
    step = max(chunk_size - overlap, 1)
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks

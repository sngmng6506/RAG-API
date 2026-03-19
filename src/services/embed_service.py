"""텍스트 → 임베딩. TEI 서버만 사용. TEI max_client_batch_size 제한 고려."""
from __future__ import annotations

import httpx

from src.core.config import settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    url = f"http://{settings.TEI_HOST}:{settings.TEI_PORT}/embed"
    batch_size = settings.TEI_MAX_BATCH_SIZE
    results: list[list[float]] = []

    with httpx.Client(timeout=60.0, verify=False) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            resp = client.post(url, json={"inputs": batch})
            if not resp.is_success:
                raise RuntimeError(f"TEI {resp.status_code}: {resp.text}")
            results.extend(resp.json())

    return results

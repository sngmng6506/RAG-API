from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    question: str
    collection_name: str | None = None
    top_k: int | None = None
    use_parent: bool = False  # True이면 자식 대신 부모 청크 텍스트 반환


class ChunkResult(BaseModel):
    text: str
    source: str
    page: int
    score: float


class RetrieveResponse(BaseModel):
    question: str
    chunks: list[ChunkResult]


class QueryRequest(BaseModel):
    question: str
    collection_name: str | None = None
    top_k: int | None = None
    use_parent: bool = False      # True이면 자식 대신 부모 청크 텍스트를 LLM context로 전달
    temperature: float = 0.1       # LLM 생성 temperature (0.0 ~ 1.0)
    max_tokens: int | None = None  # None이면 config의 RAG_MAX_TOKENS(4096) 사용


class QueryResponse(BaseModel):
    question: str
    answer: str
    chunks: list[ChunkResult]

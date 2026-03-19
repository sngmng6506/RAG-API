from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 9000

    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8501
    CHROMA_COLLECTION_NAME: str = "default"

    TEI_HOST: str = "localhost"
    TEI_PORT: int = 8080
    TEI_MAX_BATCH_SIZE: int = 8  # TEI max_client_batch_size 와 맞춤

    CHUNK_SIZE: int = 500    # 자식 청크 최대 글자 수
    CHUNK_OVERLAP: int = 50  # 청크 간 겹치는 글자 수

    PARENT_STORE_DIR: str = "data/parents"  # 부모 청크 JSON 저장 루트 디렉터리

    VLLM_LLM_HOST: str = "localhost"
    VLLM_LLM_PORT: int = 8000
    VLLM_LLM_SERVED_MODEL_NAME: str = "gpt-oss-20b"

    RAG_TOP_K: int = 5       # 검색할 자식 청크 수
    RAG_MAX_TOKENS: int = 4096  # LLM 최대 생성 토큰 (reasoning 모델은 추론에 토큰 소비)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()


PDF 문서를 벡터DB에 적재하고, LLM을 활용한 RAG(Retrieval-Augmented Generation) 질의응답 기능을 제공하는 FastAPI 기반 AI 서버입니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **Ingest** | PDF 업로드 → Hierarchical Chunking → TEI 임베딩 → ChromaDB 저장 |
| **RAG Retrieve** | 질문 임베딩 후 ChromaDB 벡터 검색, 관련 청크 반환 |
| **RAG Query** | 검색된 청크를 context로 vLLM(gpt-oss-20b) 호출, 최종 답변 생성 |
| **Collections** | ChromaDB 컬렉션 및 파일 단위 CRUD |

---

## 외부 서비스 의존성

| 서비스 | 역할 | 기본 포트 |
|--------|------|-----------|
| **ChromaDB** | 벡터 데이터베이스 | `8003` |
| **TEI** (Text Embeddings Inference) | 텍스트 임베딩 생성 (Qwen3-Embedding) | `8080` |
| **vLLM - LLM** | 답변 생성 (gpt-oss-20b) | `8000` |
| **vLLM - Coder** | 코드 생성 (Qwen2.5-Coder-7B-Instruct) | `8001` |

> TEI, vLLM은 별도 Linux 서버에서 실행 중인 서비스입니다. `.env`에서 호스트/포트를 설정합니다.

---

## 프로젝트 구조

```
MOA-server/
├── .env                          # 환경변수 (서버 접속 정보 등)
├── docker-compose.yml            # ChromaDB 컨테이너 설정
├── requirements.txt              # Python 의존성 목록
│
├── data/
│   ├── chroma_index/             # ChromaDB 로컬 데이터
│   └── parents/                  # 부모 청크 JSON ({collection_name}.json)
│
├── src/
│   ├── main.py                   # FastAPI 앱 진입점
│   │
│   ├── core/
│   │   └── config.py             # pydantic-settings 기반 설정 (Settings)
│   │
│   ├── api/v1/
│   │   ├── ingest/
│   │   │   ├── router.py         # Ingest 엔드포인트
│   │   │   └── schemas.py        # 요청/응답 Pydantic 모델
│   │   └── rag/
│   │       ├── router.py         # RAG 엔드포인트
│   │       └── schemas.py        # 요청/응답 Pydantic 모델
│   │
│   ├── services/
│   │   ├── ingest_service.py     # ChromaDB 임베딩 관련 서비스 
│   │   ├── rag_service.py        # 검색(retrieve) + 생성(generate) 서비스 
│   │   ├── embed_service.py      # TEI 임베딩 호출 서비스 
│   │   └── document_service.py   # PDF 파싱 및 Hierarchical Chunking
│   │
│   └── prompts/
│       ├── loader.py             # Jinja2 템플릿 로더
│       ├── rag_prompt.j2         # RAG 답변 생성 프롬프트
│       └── sql_prompt.j2         # SQL 생성 프롬프트 (예비)

```

---

## 빠른 시작

### 1. 환경변수 설정

`.env` 파일을 생성하고 각 서비스의 접속 정보를 입력합니다.

```env
# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8003
CHROMA_COLLECTION_NAME=default

# TEI (Text Embeddings Inference)
TEI_HOST=<TEI 서버 IP>
TEI_PORT=8080

# vLLM - LLM
VLLM_LLM_HOST=<vLLM 서버 IP>
VLLM_LLM_PORT=8000
VLLM_LLM_SERVED_MODEL_NAME=gpt-oss-20b

# vLLM - Coder
VLLM_CODER_HOST=<vLLM 서버 IP>
VLLM_CODER_PORT=8001
VLLM_CODER_SERVED_MODEL_NAME=qwen2.5-coder-7b

# App
APP_HOST=0.0.0.0
APP_PORT=9000
```

### 2. ChromaDB 실행 (Docker)

```bash
docker-compose up -d chromadb
```

### 3. Python 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 서버 실행

```bash
python -m src.main
```

또는

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 9000
```

### 5. API 문서 확인

- Swagger UI: http://localhost:9000/docs
- ReDoc: http://localhost:9000/redoc

---

## API 엔드포인트

### Ingest

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/v1/ingest/upload` | PDF 업로드 → 청킹 → 임베딩 → ChromaDB 저장 |
| `GET` | `/v1/ingest/collections` | 전체 컬렉션 목록 조회 |
| `GET` | `/v1/ingest/collections/{name}/files` | 컬렉션 내 파일 목록 조회 |
| `DELETE` | `/v1/ingest/collections/{name}` | 컬렉션 전체 삭제 |
| `DELETE` | `/v1/ingest/collections/{name}/files/{file}` | 특정 파일 청크 삭제 |

**업로드 예시 (form-data)**
```
file: 파일.pdf
collection_name: default       (선택, 기본값: .env의 CHROMA_COLLECTION_NAME)
chunk_size: 500                (선택, 기본값: 500)
chunk_overlap: 50              (선택, 기본값: 50)
```

---

### RAG

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/v1/rag/retrieve` | 질문 → 벡터 검색 → 관련 청크 반환 |
| `POST` | `/v1/rag/query` | 질문 → 검색 → LLM 답변 생성 |

**retrieve 요청 예시**
```json
{
  "question": "물류 신청 방법은?",
  "collection_name": "default",
  "top_k": 5,
  "use_parent": false
}
```

**query 요청 예시**
```json
{
  "question": "물류 신청 방법은?",
  "collection_name": "default",
  "top_k": 5,
  "use_parent": true,
  "temperature": 0.1,
  "max_tokens": 1024
}
```

> `use_parent: true` — 자식 청크로 검색 후, 연결된 부모(페이지 단위) 텍스트를 LLM context로 전달합니다.

---

## Hierarchical Chunking 구조

문서를 두 단계로 분할합니다.

```
[부모 청크: 페이지 단위]  → data/parents/{collection}.json 에 저장
    ├── [자식 청크 1]     → TEI 임베딩 → ChromaDB 저장 (벡터 검색 대상)
    ├── [자식 청크 2]
    └── [자식 청크 3]
```

- **검색**: 자식 청크 기준으로 유사도 검색
- **생성**: `use_parent=true`이면 부모 텍스트를 LLM에 전달해 더 넓은 문맥 제공

---

## 기술 스택

| 항목 | 내용 |
|------|------|
| Framework | FastAPI |
| Vector DB | ChromaDB (HttpClient) |
| Embedding | TEI (Text Embeddings Inference) |
| LLM | vLLM (OpenAI-compatible API) |
| Document Parsing | pypdf |
| Prompt | Jinja2 (.j2 템플릿) |
| Settings | pydantic-settings |
| Containerization | Docker, Docker Compose |

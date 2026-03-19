# main.py (진입점)
from fastapi import FastAPI
from src.api.v1.ingest.router import router as ingest_router
from src.api.v1.rag.router import router as rag_router
from src.core.config import settings

app = FastAPI()
app.include_router(ingest_router)
app.include_router(rag_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT)


    
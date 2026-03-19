from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.core.config import settings
from src.services.ingest_service import list_collections, upload, list_files, delete_file, delete_collection

from .schemas import (
    UploadResponse,
    CollectionsResponse,
    FilesResponse,
    DeleteFileResponse,
    DeleteCollectionResponse,
)

router = APIRouter(prefix="/v1/ingest", tags=["ingest"])


@router.get("/collections", response_model=CollectionsResponse)
def get_collections():
    names = list_collections()
    return CollectionsResponse(collections=names)


@router.get("/collections/{collection_name}/files", response_model=FilesResponse)
def get_files(collection_name: str):
    try:
        files = list_files(collection_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return FilesResponse(collection=collection_name, files=files)


@router.delete("/collections/{collection_name}/files/{file_name}", response_model=DeleteFileResponse)
def delete_file_endpoint(collection_name: str, file_name: str):
    """특정 컬렉션 내 파일(source) 청크 전체 삭제."""
    try:
        result = delete_file(collection_name, file_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return DeleteFileResponse(collection=collection_name, file=file_name, **result)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str | None = Form(None),
    chunk_size: int | None = Form(None),
    chunk_overlap: int | None = Form(None),
):
    """
    PDF 업로드 → 파싱(Hierarchical Chunking) → 임베딩 → Chroma 저장.
    chunk_size / chunk_overlap: 미입력 시 서버 기본값(.env) 사용.
    """
    name = collection_name or settings.CHROMA_COLLECTION_NAME
    content = await file.read()
    try:
        result = upload(
            name,
            content,
            file.filename or "unknown",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return UploadResponse(collection=name, **result)


@router.delete("/collections/{collection_name}", response_model=DeleteCollectionResponse)
def delete_collection_endpoint(collection_name: str):
    """컬렉션 전체 삭제."""
    try:
        delete_collection(collection_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return DeleteCollectionResponse(collection=collection_name, deleted=True)





from pydantic import BaseModel


class UploadResponse(BaseModel):
    collection: str
    parents_added: int
    children_added: int


class CollectionsResponse(BaseModel):
    collections: list[str]


class FilesResponse(BaseModel):
    collection: str
    files: list[str]


class DeleteFileResponse(BaseModel):
    collection: str
    file: str
    children_deleted: int
    parents_deleted: int


class DeleteCollectionResponse(BaseModel):
    collection: str
    deleted: bool

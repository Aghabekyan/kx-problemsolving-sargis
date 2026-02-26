from pydantic import BaseModel


class StorageStatus(BaseModel):
    url: str
    status: str


class StatusResponse(BaseModel):
    services: list[StorageStatus]


class DataItem(BaseModel):
    id: int
    name: str
    value: str


class DataResponse(BaseModel):
    instance: str
    data: list[DataItem]


class ErrorResponse(BaseModel):
    detail: str

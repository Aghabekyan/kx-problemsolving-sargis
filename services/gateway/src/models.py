from __future__ import annotations

from pydantic import BaseModel


class DataItem(BaseModel):
    id: int
    name: str
    value: str


class DataResponse(BaseModel):
    instance: str
    data: list[DataItem]


DataResponse.model_rebuild()


class StorageStatus(BaseModel):
    url: str
    status: str


class StatusResponse(BaseModel):
    services: list[StorageStatus]

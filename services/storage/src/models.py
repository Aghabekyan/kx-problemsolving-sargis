from pydantic import BaseModel


class DataItem(BaseModel):
    id: int
    name: str
    value: str


class DataResponse(BaseModel):
    instance: str
    data: list[DataItem]


class HealthResponse(BaseModel):
    status: str
    instance: str

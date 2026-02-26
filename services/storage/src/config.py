from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    instance_id: str = "storage-unknown"


settings = Settings()

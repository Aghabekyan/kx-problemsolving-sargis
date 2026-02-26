from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    storage_services: str = ""
    request_timeout: float = 2.0
    health_check_interval: float = 5.0


    @property
    def storage_urls(self) -> list[str]:
        urls = [url.strip() for url in self.storage_services.split(",") if url.strip()]
        if not urls:
            raise ValueError("STORAGE_SERVICES must include at least one URL")
        return urls

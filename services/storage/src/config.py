from pydantic_settings import BaseSettings



class Settings(BaseSettings):
    service_name: str = ""


    @property
    def instance_name(self) -> str:
        value =  self.service_name.strip()
        if not value:
            raise ValueError("SERVICE_NAME must be set")
        return value
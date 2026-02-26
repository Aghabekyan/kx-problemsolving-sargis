from fastapi import FastAPI

from .config import settings
from .routes import router


app = FastAPI(
    title=f"Storage Service ({settings.instance_id})",
)

app.include_router(router)

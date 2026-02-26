from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes import router, shutdown_event, startup_event



@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event(app)
    try:
        yield
    finally:
        await shutdown_event(app)


app = FastAPI(title="Gateway Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

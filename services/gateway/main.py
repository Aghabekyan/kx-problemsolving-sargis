from fastapi import FastAPI

from routes import router, shutdown_event, startup_event


app = FastAPI(title="Gateway Service", version="1.0.0")
app.include_router(router)


@app.on_event("startup")
async def on_startup() -> None:
    await startup_event()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await shutdown_event()

from fastapi import FastAPI

from src.backend.app.api.operations import router as operations_router

app = FastAPI(
    title="PortFlow API",
    version="1.0.0",
    description="Congestion prediction and port operations optimization API.",
)
app.include_router(operations_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "portflow-api"}
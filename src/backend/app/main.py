from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.app.api.operations import router as operations_router

app = FastAPI(
    title="PortFlow API",
    version="1.0.0",
    description="Congestion prediction and port operations optimization API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(operations_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "portflow-api"}
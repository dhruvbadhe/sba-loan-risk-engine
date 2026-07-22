import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.api import routes_auth, routes_predict
from app.middleware.logging_middleware import LoggingMiddleware

logging.basicConfig(level=logging.INFO, format = "%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title=settings.APP_NAME,
    description="Risk Assessment & Basel-II Expected Loss Engine API for SBA 7(a) Loans",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

app.add_middleware(LoggingMiddleware)

Instrumentator().instrument(app).expose(app)

app.include_router(routes_auth.router)
app.include_router(routes_predict.router)

@app.get("/health", tags=["System Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000

        logger.info(
            f"Client IP: {request.client.host} | Method: {request.method} |"
            f"Path: {request.url.path} | Status: {response.status_code} | "
            f"Latency: {process_time:.2f}ms"

        )
        return response
    

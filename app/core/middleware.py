from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logging import logger

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID", "anonymous")
        
        logger.info("incoming_request", extra={
            "method": request.method,
            "path": request.url.path,
            "tenant_id": tenant_id
        })

        response = await call_next(request)

        logger.info("outgoing_response", extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "tenant_id": tenant_id
        })

        return response
    
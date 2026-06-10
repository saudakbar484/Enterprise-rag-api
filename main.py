import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.core.database import init_db
from app.core.vector_store import init_vector_store
from app.api.v1.documents import router as documents_router
from app.core.logging import logger
from app.core.exceptions import (
    http_exception_handler,
    sqlalchemy_exception_handler,
    global_exception_handler,
)
from app.core.middleware import LoggingMiddleware
from app.api.routes import router as health_router
from app.api.v1.tenants import router as tenants_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"app": settings.app_name})
    await init_db()
    init_vector_store()
    yield
    logger.info("shutdown", extra={"app": settings.app_name})


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(LoggingMiddleware)

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

app.include_router(health_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1/tenants")

app.include_router(documents_router, prefix="/api/v1/documents")

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=settings.port, reload=settings.debug
    )
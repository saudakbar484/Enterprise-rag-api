from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.tasks.ingest import ingest_document
from app.core.logging import logger

router = APIRouter()


@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    # Read file
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    # Hand off to Celery — return immediately
    task = ingest_document.delay(
        text=text,
        doc_filename=file.filename,
        tenant_id=tenant.id,
    )

    logger.info("ingest_queued", extra={
        "task_id": task.id,
        "tenant_id": tenant.id,
        "doc_filename": file.filename,
    })

    return {
        "status": "accepted",
        "task_id": task.id,
        "message": "Document queued for processing",
    }


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    tenant: Tenant = Depends(get_current_tenant),
):
    from app.core.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }
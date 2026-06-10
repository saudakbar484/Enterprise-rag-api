from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.dependencies import get_current_tenant
from app.models.tenant import Tenant
from app.tasks.ingest import ingest_document
from app.core.celery_app import celery_app
from app.core.logging import logger

router = APIRouter()


@router.post("/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    tenant: Tenant = Depends(get_current_tenant),
):
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

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


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    tenant: Tenant = Depends(get_current_tenant),
):
    result = celery_app.AsyncResult(task_id)

    # Map Celery states to clean response
    state = result.state

    if state == "PENDING":
        return {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "detail": "Task is waiting to be picked up by a worker",
        }

    elif state == "STARTED":
        return {
            "task_id": task_id,
            "status": "started",
            "progress": 5,
            "detail": "Worker has picked up the task",
        }

    elif state == "PROGRESS":
        meta = result.info or {}
        return {
            "task_id": task_id,
            "status": "processing",
            "progress": meta.get("progress", 0),
            "stage": meta.get("stage", "unknown"),
            "detail": f"Processing stage: {meta.get('stage', 'unknown')}",
        }

    elif state == "SUCCESS":
        return {
            "task_id": task_id,
            "status": "complete",
            "progress": 100,
            "result": result.result,
        }

    elif state == "FAILURE":
        return {
            "task_id": task_id,
            "status": "failed",
            "progress": 0,
            "detail": str(result.info),
        }

    else:
        return {
            "task_id": task_id,
            "status": state.lower(),
            "progress": 0,
        }
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.export_schema import (
    ExportJobCreateRequest,
    ExportJobCreateResponse,
    ExportJobStatusResponse,
)
from app.utils.date_helpers import ensure_utc
from app.services import export_service
from app.services.minio_service import MinioService

router = APIRouter()


@router.post(
    "/supervisor/{supervisor_id}",
    response_model=ExportJobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_export_job(
    supervisor_id: str,
    payload: ExportJobCreateRequest,
    background_tasks: BackgroundTasks,
):
    try:
        job_id = await export_service.create_export_job(supervisor_id, payload)
        background_tasks.add_task(export_service.process_export_job, job_id)

        return ExportJobCreateResponse(
            job_id=job_id,
            status="processing",
            message="Exportación en proceso",
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{job_id}",
    response_model=ExportJobStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_export_job_status(job_id: str):
    job = await export_service.get_export_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )

    file_data = job.get("file") or {}

    return ExportJobStatusResponse(
        job_id=job["_id"],
        status=job["status"],
        type=job["type"],
        format=job["format"],
        file_name=file_data.get("file_name"),
        expires_at=file_data.get("expires_at"),
        error=job.get("error"),
    )


@router.get("/{job_id}/download")
async def download_export_file(job_id: str):
    job = await export_service.get_export_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export job not found",
        )

    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Export file is not ready yet",
        )

    file_data = job.get("file")
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file metadata not found",
        )

    expires_at = file_data.get("expires_at")
    if expires_at:
        expires_at = ensure_utc(expires_at)
    
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Export file has expired",
            )

    minio_service = MinioService()
    obj = minio_service.get_object(file_data["object_key"])

    def iter_chunks():
        try:
            for chunk in obj.stream(32 * 1024):
                yield chunk
        finally:
            obj.close()
            obj.release_conn()

    return StreamingResponse(
        iter_chunks(),
        media_type=file_data["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{file_data["file_name"]}"'
        },
    )
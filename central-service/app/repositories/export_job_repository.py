from datetime import datetime, timezone
from bson import ObjectId

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document


async def create_export_job(document: dict) -> str:
    db = await get_db()
    result = await db["export_jobs"].insert_one(document)
    return str(result.inserted_id)


async def get_export_job_by_id(job_id: str):
    db = await get_db()
    if not ObjectId.is_valid(job_id):
        return None
    document = await db["export_jobs"].find_one({"_id": ObjectId(job_id)})
    return serialize_document(document)


async def mark_export_job_completed(job_id: str, file_data: dict):
    db = await get_db()
    await db["export_jobs"].update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": "completed",
                "file": file_data,
                "completed_at": datetime.now(timezone.utc),
            }
        },
    )


async def mark_export_job_failed(job_id: str, error: str):
    db = await get_db()
    await db["export_jobs"].update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "status": "failed",
                "error": error,
                "completed_at": datetime.now(timezone.utc),
            }
        },
    )
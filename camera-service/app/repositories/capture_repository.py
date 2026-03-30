from datetime import datetime
from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document

async def create_capture_session(session_data: dict) -> dict:
    db = await get_db()
    collection = db["capture_sessions"]
    await collection.insert_one(session_data)

    return serialize_document(session_data)

async def get_active_session_by_camera_id(camera_id: str) -> dict | None:
    db = await get_db()
    collection = db["capture_sessions"]

    doc = await collection.find_one({
        "camera_id": camera_id,
        "active": True
    })

    return serialize_document(doc)

async def get_session_by_id(session_id: str) -> dict | None:
    db = await get_db()
    collection = db["capture_sessions"]

    doc = await collection.find_one({"_id": session_id})

    return serialize_document(doc)

async def close_capture_session(session_id: str) -> dict | None:
    db = await get_db()
    collection = db["capture_sessions"]

    await collection.update_one(
        {"_id": session_id, "active": True},
        {
            "$set": {
                "active": False,
                "ended_at": datetime.utcnow()
            }
        }
    )

    updated = await collection.find_one({"_id": session_id})

    return serialize_document(updated)
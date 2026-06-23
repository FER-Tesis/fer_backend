from app.db.connection import get_db
from datetime import datetime, timezone

async def get_current_status(camera_id: str):
    db = await get_db()
    collection = db["current_emotion_status"]
    return await collection.find_one({"camera_id": camera_id})


async def get_all_statuses(limit: int = 100):
    db = await get_db()
    items = await db["current_emotion_status"].find().to_list(limit)
    return items


async def get_status_by_camera_id(camera_id: str):
    db = await get_db()
    return await db["current_emotion_status"].find_one({"camera_id": camera_id})

async def get_status_by_agent_id(agent_id: str):
    db = await get_db()
    collection = db["current_emotion_status"]
    return await collection.find_one({"agent_id": agent_id})


async def upsert_status_if_newer(
    camera_id: str,
    agent_id: str,
    emotion: str,
    timestamp,
) -> bool:
    db = await get_db()
    collection = db["current_emotion_status"]

    now = datetime.utcnow()

    result = await collection.update_one(
        {
            "camera_id": camera_id,
            "agent_id": agent_id,
        },
        {
            "$set": {
                "camera_id": camera_id,
                "agent_id": agent_id,
                "emotion": emotion,
                "timestamp": timestamp,
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )

    return result.modified_count > 0 or result.upserted_id is not None

async def delete_status_by_agent_id(agent_id: str):
    db = await get_db()
    collection = db["current_emotion_status"]
    await collection.delete_many({"agent_id": agent_id})
from datetime import datetime

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list

async def create_emotion_event(event_data: dict) -> dict:
    db = await get_db()
    collection = db["emotion_events"]
    result = await collection.insert_one(event_data)
    event_data["_id"] = result.inserted_id
    return serialize_document(event_data)

async def get_emotion_events(limit: int = 100):
    db = await get_db()
    collection = db["emotion_events"]
    items = await collection.find().sort("timestamp", -1).to_list(limit)
    return serialize_list(items)

async def get_emotion_events_for_agent_between(
    agent_id: str,
    start: datetime,
    end: datetime,
):
    db = await get_db()
    collection = db["emotion_events"]

    cursor = (
        collection.find(
            {
                "agent_id": agent_id,
                "timestamp": {"$gte": start, "$lte": end},
            }
        )
        .sort("timestamp", 1)
    )

    items = await cursor.to_list(length=None)
    return serialize_list(items)

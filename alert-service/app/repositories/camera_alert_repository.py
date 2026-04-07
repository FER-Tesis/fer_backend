from bson import ObjectId

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list


async def create_camera_alert(alert_data: dict) -> dict:
    db = await get_db()
    collection = db["camera_alerts"]

    result = await collection.insert_one(alert_data)
    alert_data["_id"] = result.inserted_id

    return serialize_document(alert_data)


async def get_camera_alert_by_id(alert_id: str):
    db = await get_db()
    collection = db["camera_alerts"]

    item = await collection.find_one({"_id": ObjectId(alert_id)})
    return serialize_document(item)


async def get_active_alert_by_camera_id(camera_id: str):
    db = await get_db()
    collection = db["camera_alerts"]

    item = await collection.find_one(
        {
            "camera_id": camera_id,
            "status": "active",
        }
    )

    return serialize_document(item)


async def resolve_camera_alert(alert_id: str):
    db = await get_db()
    collection = db["camera_alerts"]

    await collection.update_one(
        {"_id": ObjectId(alert_id)},
        {"$set": {"status": "resolved"}},
    )


async def delete_camera_alert(alert_id: str):
    db = await get_db()
    collection = db["camera_alerts"]

    await collection.delete_one({"_id": ObjectId(alert_id)})


async def get_camera_alerts(limit: int = 100):
    db = await get_db()
    collection = db["camera_alerts"]

    items = await collection.find().sort("created_at", -1).to_list(limit)
    return serialize_list(items)


async def get_active_camera_alerts_for_agent(
    agent_id: str,
    limit: int = 100,
):
    db = await get_db()
    collection = db["camera_alerts"]

    items = await collection.find(
        {
            "agent_id": agent_id,
            "status": "active",
        }
    ).sort("created_at", -1).to_list(limit)

    return serialize_list(items)


async def get_active_camera_alerts_for_agents(
    agent_ids: list[str],
    limit: int = 100,
):
    db = await get_db()
    collection = db["camera_alerts"]

    items = await collection.find(
        {
            "agent_id": {"$in": agent_ids},
            "status": "active",
        }
    ).sort("created_at", -1).to_list(limit)

    return serialize_list(items)


async def get_camera_alert_history_for_agents(
    agent_ids: list[str],
    limit: int = 100,
):
    db = await get_db()
    collection = db["camera_alerts"]

    items = await collection.find(
        {
            "agent_id": {"$in": agent_ids},
        }
    ).sort("created_at", -1).to_list(limit)

    return serialize_list(items)


async def ensure_camera_alert_indexes():
    db = await get_db()
    collection = db["camera_alerts"]

    await collection.create_index(
        [("camera_id", 1), ("status", 1)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="uq_active_camera_alert_per_camera",
    )

    await collection.create_index(
        [("agent_id", 1), ("status", 1)],
        name="idx_camera_alert_agent_status",
    )

    await collection.create_index(
        [("created_at", -1)],
        name="idx_camera_alert_created_at",
    )
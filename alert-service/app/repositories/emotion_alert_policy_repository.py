from datetime import datetime
from bson import ObjectId

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list


async def create_policy(policy_data: dict) -> dict:
    db = await get_db()
    collection = db["emotion_alert_policies"]
    policy_data["created_at"] = datetime.utcnow()
    policy_data["updated_at"] = datetime.utcnow()
    result = await collection.insert_one(policy_data)
    policy_data["_id"] = result.inserted_id
    return serialize_document(policy_data)


async def get_policy_by_id(policy_id: str) -> dict | None:
    db = await get_db()
    collection = db["emotion_alert_policies"]
    doc = await collection.find_one({"_id": ObjectId(policy_id)})
    return serialize_document(doc) if doc else None


async def get_active_policy_by_supervisor(supervisor_id: str) -> dict | None:
    db = await get_db()
    collection = db["emotion_alert_policies"]
    doc = await collection.find_one({
        "supervisor_id": ObjectId(supervisor_id),
        "status": "active"
    })
    return serialize_document(doc) if doc else None


async def get_all_policies_by_supervisor(supervisor_id: str) -> list[dict]:
    db = await get_db()
    collection = db["emotion_alert_policies"]
    cursor = collection.find({"supervisor_id": ObjectId(supervisor_id)})
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def update_policy(policy_id: str, update_data: dict) -> dict | None:
    db = await get_db()
    collection = db["emotion_alert_policies"]
    update_data["updated_at"] = datetime.utcnow()
    result = await collection.find_one_and_update(
        {"_id": ObjectId(policy_id)},
        {"$set": update_data},
        return_document=True
    )
    return serialize_document(result) if result else None


async def deactivate_all_supervisor_policies(supervisor_id: str):
    db = await get_db()
    collection = db["emotion_alert_policies"]
    await collection.update_many(
        {"supervisor_id": ObjectId(supervisor_id)},
        {"$set": {"status": "inactive", "updated_at": datetime.utcnow()}}
    )

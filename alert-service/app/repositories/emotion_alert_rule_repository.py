from datetime import datetime
from bson import ObjectId

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list


async def create_rule(rule_data: dict) -> dict:
    db = await get_db()
    collection = db["emotion_alert_rules"]
    rule_data["created_at"] = datetime.utcnow()
    rule_data["updated_at"] = datetime.utcnow()
    result = await collection.insert_one(rule_data)
    rule_data["_id"] = result.inserted_id
    return serialize_document(rule_data)


async def get_rule_by_id(rule_id: str) -> dict | None:
    db = await get_db()
    collection = db["emotion_alert_rules"]
    doc = await collection.find_one({"_id": ObjectId(rule_id)})
    return serialize_document(doc) if doc else None


async def get_active_rules_by_policy(policy_id: str) -> list[dict]:
    db = await get_db()
    collection = db["emotion_alert_rules"]
    cursor = collection.find({
        "policy_id": ObjectId(policy_id),
        "status": "active"
    })
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def get_all_rules_by_policy(policy_id: str) -> list[dict]:
    db = await get_db()
    collection = db["emotion_alert_rules"]
    cursor = collection.find({"policy_id": ObjectId(policy_id)})
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def update_rule(rule_id: str, update_data: dict) -> dict | None:
    db = await get_db()
    collection = db["emotion_alert_rules"]
    update_data["updated_at"] = datetime.utcnow()
    result = await collection.find_one_and_update(
        {"_id": ObjectId(rule_id)},
        {"$set": update_data},
        return_document=True
    )
    return serialize_document(result) if result else None


async def delete_evaluation_states_by_rule(rule_id: str):
    """Eliminar todos los estados de evaluación de una regla"""
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    await collection.delete_many({"rule_id": ObjectId(rule_id)})

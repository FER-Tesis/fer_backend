from datetime import datetime
from bson import ObjectId

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list


async def create_alert(alert_data: dict) -> dict:
    """Crear una nueva alerta emocional"""
    db = await get_db()
    collection = db["emotion_alerts"]
    alert_data["created_at"] = datetime.utcnow()
    alert_data["updated_at"] = datetime.utcnow()
    result = await collection.insert_one(alert_data)
    alert_data["_id"] = result.inserted_id
    return serialize_document(alert_data)


async def get_alert_by_id(alert_id: str) -> dict | None:
    db = await get_db()
    collection = db["emotion_alerts"]
    doc = await collection.find_one({"_id": ObjectId(alert_id)})
    return serialize_document(doc) if doc else None


async def get_alerts_by_agent(agent_id: str, limit: int = 100) -> list[dict]:
    """Obtener todas las alertas de un agente"""
    db = await get_db()
    collection = db["emotion_alerts"]
    cursor = collection.find({"agent_id": agent_id}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def get_alerts_by_supervisor(supervisor_id: str, limit: int = 100) -> list[dict]:
    """Obtener todas las alertas de un supervisor"""
    db = await get_db()
    collection = db["emotion_alerts"]
    cursor = collection.find({"supervisor_id": supervisor_id}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def get_alerts_by_status(status: str, limit: int = 100) -> list[dict]:
    """Obtener todas las alertas por estado"""
    db = await get_db()
    collection = db["emotion_alerts"]
    cursor = collection.find({"status": status}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def get_pending_alerts(limit: int = 100) -> list[dict]:
    """Obtener todas las alertas pendientes"""
    return await get_alerts_by_status("pending", limit)


async def update_alert(alert_id: str, update_data: dict) -> dict | None:
    """Actualizar una alerta"""
    db = await get_db()
    collection = db["emotion_alerts"]
    update_data["updated_at"] = datetime.utcnow()
    result = await collection.find_one_and_update(
        {"_id": ObjectId(alert_id)},
        {"$set": update_data},
        return_document=True
    )
    return serialize_document(result) if result else None


async def get_alerts_by_agent_and_supervisor(agent_id: str, supervisor_id: str, limit: int = 100) -> list[dict]:
    """Obtener alertas de un agente específico bajo un supervisor"""
    db = await get_db()
    collection = db["emotion_alerts"]
    cursor = collection.find({
        "agent_id": agent_id,
        "supervisor_id": supervisor_id
    }).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)

async def get_pending_alerts_by_agent(agent_id: str, limit: int = 100) -> list[dict]:
    db = await get_db()
    collection = db["emotion_alerts"]

    cursor = collection.find({
        "agent_id": agent_id,
        "status": "pending",
    }).sort("created_at", -1).limit(limit)

    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def get_pending_alerts_by_agents(agent_ids: list[str], limit: int = 100) -> list[dict]:
    db = await get_db()
    collection = db["emotion_alerts"]

    cursor = collection.find({
        "agent_id": {"$in": agent_ids},
        "status": "pending",
    }).sort("created_at", -1).limit(limit)

    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def delete_alerts_by_agent(agent_id: str) -> int:
    """Eliminar todas las alertas emocionales de un agente"""
    db = await get_db()
    collection = db["emotion_alerts"]
    result = await collection.delete_many({"agent_id": agent_id})
    return result.deleted_count

async def delete_alerts_by_agent_id(agent_id: str) -> int:
    db = await get_db()
    collection = db["emotion_alerts"]
    result = await collection.delete_many({"agent_id": agent_id})
    return result.deleted_count
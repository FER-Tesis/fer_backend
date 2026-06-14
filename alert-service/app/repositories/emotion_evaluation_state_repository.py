from datetime import datetime
from bson import ObjectId

from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list


async def get_or_create_evaluation_state(agent_id: str, rule_id: str, policy_id: str) -> dict:
    """Obtener o crear estado de evaluación para (agent, rule, policy)"""
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    
    query = {
        "agent_id": agent_id,
        "rule_id": rule_id,
        "policy_id": policy_id,
    }
    
    # Intentar obtener
    doc = await collection.find_one(query)
    
    if doc:
        return serialize_document(doc)
    
    # Crear nuevo
    state_data = {
        **query,
        "current_count": 0,
        "emotions_window": [],
        "continuous_emotion_start": None,
        "continuous_duration_seconds": 0,
        "last_alert_at": None,
        "cooldown_end_at": None,
        "updated_at": datetime.utcnow(),
    }
    
    result = await collection.insert_one(state_data)
    state_data["_id"] = result.inserted_id
    return serialize_document(state_data)


async def update_evaluation_state(state_id: str, update_data: dict) -> dict | None:
    """Actualizar estado de evaluación"""
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    
    update_data["updated_at"] = datetime.utcnow()
    
    result = await collection.find_one_and_update(
        {"_id": ObjectId(state_id)},
        {"$set": update_data},
        return_document=True
    )
    return serialize_document(result) if result else None


async def get_evaluation_state_by_id(state_id: str) -> dict | None:
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    doc = await collection.find_one({"_id": ObjectId(state_id)})
    return serialize_document(doc) if doc else None


async def get_evaluation_states_by_agent_and_policy(agent_id: str, policy_id: str) -> list[dict]:
    """Obtener todos los estados de evaluación de un agente para una política"""
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    cursor = collection.find({
        "agent_id": agent_id,
        "policy_id": policy_id,
    })
    docs = await cursor.to_list(length=None)
    return serialize_list(docs)


async def delete_evaluation_states_by_policy(policy_id: str):
    """Eliminar todos los estados de evaluación de una política"""
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    await collection.delete_many({"policy_id": policy_id})


async def delete_evaluation_states_by_agent_and_policy(agent_id: str, policy_id: str):
    """Eliminar todos los estados de evaluación de un agente en una política"""
    db = await get_db()
    collection = db["emotion_evaluation_states"]
    await collection.delete_many({
        "agent_id": agent_id,
        "policy_id": policy_id,
    })

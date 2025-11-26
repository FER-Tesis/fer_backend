from bson import ObjectId
from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list

async def create_relation(data: dict):
    db = await get_db()
    collection = db["relations"]

    result = await collection.insert_one(data)
    data["_id"] = result.inserted_id

    return serialize_document(data)

async def get_all_relations():
    db = await get_db()
    return await db["relations"].find().to_list(None)

async def get_by_supervisor(supervisor_id: str, limit: int = 200):
    db = await get_db()
    collection = db["relations"]

    relations = await collection.find({"supervisor_id": supervisor_id}).to_list(limit)
    return serialize_list(relations)

async def delete_relation(relation_id: str):
    db = await get_db()
    collection = db["relations"]

    if not ObjectId.is_valid(relation_id):
        return False

    result = await collection.delete_one({"_id": ObjectId(relation_id)})
    return result.deleted_count == 1

async def remove_by_supervisor_agent(supervisor_id: str, agent_id: str) -> bool:
    db = await get_db()
    collection = db["relations"]

    record = await collection.find_one({
        "supervisor_id": supervisor_id,
        "agent_id": agent_id
    })

    if not record:
        return False

    result = await collection.delete_one({
        "_id": record["_id"]
    })

    return result.deleted_count == 1

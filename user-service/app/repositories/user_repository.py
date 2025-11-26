from bson import ObjectId
from app.db.connection import get_db
from app.schemas.user_schema import UserCreate
from app.utils.mongo_helpers import serialize_document, serialize_list

async def create_user(user_data: dict):
    db = await get_db()
    collection = db["users"]

    result = await collection.insert_one(user_data)
    user_data["_id"] = result.inserted_id
    user_data.pop("password", None)

    return serialize_document(user_data)


async def get_all_users(limit: int = 100):
    db = await get_db()
    collection = db["users"]

    users = await collection.find().to_list(limit)
    return serialize_list(users)


async def get_user_by_id(user_id: str):
    db = await get_db()
    collection = db["users"]

    if not ObjectId.is_valid(user_id):
        return None

    user = await collection.find_one({"_id": ObjectId(user_id)})
    return serialize_document(user)


async def update_user(user_id: str, data: dict):
    db = await get_db()
    collection = db["users"]

    if not ObjectId.is_valid(user_id):
        return None

    result = await collection.update_one({"_id": ObjectId(user_id)}, {"$set": data})
    if result.modified_count == 1:
        updated_user = await get_user_by_id(user_id)
        return serialize_document(updated_user)
    return None


async def delete_user(user_id: str):
    db = await get_db()
    collection = db["users"]

    if not ObjectId.is_valid(user_id):
        return False

    result = await collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count == 1

async def get_user_by_email(email: str):
    db = await get_db()
    collection = db["users"]

    user = await collection.find_one({"email": email})
    
    return serialize_document(user)

async def count_all_users():
    db = await get_db()
    collection = db["users"]
    return await collection.count_documents({})


async def count_active_agents():
    db = await get_db()
    collection = db["users"]
    return await collection.count_documents({
        "role": "agent",
        "is_active": True
    })

async def get_users_by_role(role: str):
    db = await get_db()
    collection = db["users"]
    return await collection.find({"role": role}).to_list(None)

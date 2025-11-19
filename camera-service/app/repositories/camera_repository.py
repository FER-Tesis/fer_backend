from datetime import datetime
from bson import ObjectId
from app.db.connection import get_db
from app.utils.mongo_helpers import serialize_document, serialize_list

async def create_camera(camera_data: dict) -> dict:
    db = await get_db()
    collection = db["cameras"]
    camera_data["last_checked"] = camera_data.get("last_checked") or datetime.utcnow()
    result = await collection.insert_one(camera_data)
    camera_data["_id"] = result.inserted_id

    return serialize_document(camera_data)

async def get_all_cameras(limit: int = 100) -> list[dict]:
    db = await get_db()
    collection = db["cameras"]
    items = await collection.find().to_list(limit)

    return serialize_list(items)

async def get_camera_by_id(camera_id: str) -> dict | None:
    if not ObjectId.is_valid(camera_id):
        return None
    
    db = await get_db()
    collection = db["cameras"]
    doc = await collection.find_one({"_id": ObjectId(camera_id)})

    return serialize_document(doc)

async def get_camera_by_ip(ip_address: str) -> dict | None:
    db = await get_db()
    collection = db["cameras"]
    doc = await collection.find_one({"ip_address": ip_address})

    return serialize_document(doc)

async def update_camera(camera_id: str, data: dict) -> dict | None:
    if not ObjectId.is_valid(camera_id):
        return None
    
    db = await get_db()
    collection = db["cameras"]
    data = {k: v for k, v in data.items() if v is not None}
    data["last_checked"] = datetime.utcnow()
    result = await collection.update_one({"_id": ObjectId(camera_id)}, {"$set": data})

    if result.modified_count == 0:
        doc = await collection.find_one({"_id": ObjectId(camera_id)})
        return serialize_document(doc)
    
    updated = await collection.find_one({"_id": ObjectId(camera_id)})

    return serialize_document(updated)

async def delete_camera(camera_id: str) -> bool:
    if not ObjectId.is_valid(camera_id):
        return False
    
    db = await get_db()
    collection = db["cameras"]
    res = await collection.delete_one({"_id": ObjectId(camera_id)})
    
    return res.deleted_count == 1

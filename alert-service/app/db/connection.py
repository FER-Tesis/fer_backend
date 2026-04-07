import motor.motor_asyncio
from app.core.config import settings

client = None
db = None

async def connect_db():
    global client, db
    if not settings.MONGO_URI:
        raise ValueError("No se encontró la variable MONGO_URI")

    client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
    db = client.get_default_database()
    print("Conectado a MongoDB Atlas")

async def close_db():
    global client
    if client:
        client.close()
        print("Conexión a MongoDB cerrada")

async def get_db():
    return db

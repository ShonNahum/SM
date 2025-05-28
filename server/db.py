from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db]

# Collection for key-value pairs
kv_collection = db["kvstore"]

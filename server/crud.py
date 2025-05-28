from .db import kv_collection
from .models import KeyValue
from typing import Optional

async def upsert_key_value(kv: KeyValue) -> None:
    await kv_collection.update_one(
        {"key": kv.key},
        {"$set": {"value": kv.value}},
        upsert=True
    )

async def get_value_by_key(key: str) -> Optional[str]:
    doc = await kv_collection.find_one({"key": key})
    if doc:
        return doc.get("value")
    return None

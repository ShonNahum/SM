from fastapi import FastAPI, HTTPException
from app.models import KeyValue, KeyResponse
from app.crud import upsert_key_value, get_value_by_key
import uvicorn

app = FastAPI(title="Key-Value Store Microservice")

@app.post("/kv", status_code=201)
async def set_key_value(kv: KeyValue):
    await upsert_key_value(kv)
    return {"message": f"Key '{kv.key}' updated successfully."}

@app.get("/kv/{key}", response_model=KeyResponse)
async def get_key_value(key: str):
    value = await get_value_by_key(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return KeyResponse(key=key, value=value)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
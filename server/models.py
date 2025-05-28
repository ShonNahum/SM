from pydantic import BaseModel

class KeyValue(BaseModel):
    key: str
    value: str

class KeyResponse(BaseModel):
    key: str
    value: str | None = None

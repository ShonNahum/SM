from pydantic import BaseSettings

class Settings(BaseSettings):
    mongo_uri: str
    mongo_db: str

    class Config:
        env_file = ".env"

settings = Settings()

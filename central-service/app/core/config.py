from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "central-service"
    MONGO_URI: str = ""
    USER_SERVICE_URL: str = ""
    CAMERA_SERVICE_URL: str = ""
    REDIS_URL: str = ""

    MINIO_ENDPOINT: str = ""
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "exports"
    MINIO_SECURE: bool = False

    EXPORT_FILE_TTL_MINUTES: int = 20

    class Config:
        env_file = ".env"

settings = Settings()

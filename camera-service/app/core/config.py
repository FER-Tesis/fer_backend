from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "camera-service"
    MONGO_URI: str = ""
    USER_SERVICE_URL: str = ""
    ALERT_SERVICE_URL: str = ""
    CAMERA_HUB_URL: str = ""
    REDIS_URL: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
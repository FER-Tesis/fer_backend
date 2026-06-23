from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "user-service"
    MONGO_URI: str = ""
    CENTRAL_SERVICE_URL: str = ""
    ALERT_SERVICE_URL: str = ""
    REDIS_URL: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
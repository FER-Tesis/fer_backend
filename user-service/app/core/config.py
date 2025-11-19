from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "user-service"
    MONGO_URI: str = ""
    
    class Config:
        env_file = ".env"

settings = Settings()
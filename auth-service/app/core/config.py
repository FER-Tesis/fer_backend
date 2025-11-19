from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "auth-service"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    USER_SERVICE_URL: str

    class Config:
        env_file = ".env"

settings = Settings()

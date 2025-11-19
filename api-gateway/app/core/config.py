from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "api-gateway"
    USER_SERVICE_URL: str = ""
    AUTH_SERVICE_URL: str = ""
    CAMERAS_SERVICE_URL: str = ""
    CENTRAL_SERVICE_URL: str = ""
    ALERTS_SERVICE_URL: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
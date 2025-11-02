from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGO_URI: str
    DATABASE_NAME: str
    CLASSES_API_BASE_URL: str
    OAUTH_INTERNAL_HOST: str = "oauth"
    OAUTH_INTERNAL_API_PORT: int = 8000

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
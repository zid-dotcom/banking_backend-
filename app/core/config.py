from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Banking Software"
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    SUPERADMIN_EMAIL: str
    SUPERADMIN_PASSWORD: str
    SUPERADMIN_NAME: str = "Super Admin"
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    SPACES_BUCKET: str | None = None
    SPACES_REGION: str | None = None
    SPACES_ENDPOINT: str | None = None
    SPACES_ACCESS_KEY: str | None = None
    SPACES_SECRET_KEY: str | None = None
    SPACES_PUBLIC_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/chessalytics"
    DB_ECHO: bool = False

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

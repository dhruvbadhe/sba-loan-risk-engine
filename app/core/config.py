import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME : str = "SBA Loan Risk Assessment API"
    ENV : str = "development"
    DEBUG : bool = False
    API_KEY: str = Field(default="dev-key-change-in-production")
    JWT_SECRET_KEY: str = Field(default="super-secret-key-change-for-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    MODEL_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "models", "best_hgb_pipeline.pkl"
    )
    # Cache Configurations
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    
    # Supabase Database Configurations
    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")
    
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
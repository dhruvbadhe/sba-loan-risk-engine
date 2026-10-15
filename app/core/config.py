import os
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME : str = "SBA Loan Risk Assessment API"
    ENV : str = "development"
    DEBUG : bool = False
    API_KEY: str = Field(default="dev-key-change-in-production")
    JWT_SECRET_KEY: str = Field(default="super-secret-key-change-for-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:8501,http://127.0.0.1:8501,http://localhost:8000,http://127.0.0.1:8000"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def reject_wildcard_origins(cls, value):
        if "*" in value:
            raise ValueError("CORS_ORIGINS must contain explicit origins, not wildcards")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    MODEL_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "models", "best_hgb_pipeline.pkl"
    )

    REDIS_URL: str = Field(default="redis://localhost:6379/0")


    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")


    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENV == "production":
            for name in ("API_KEY", "JWT_SECRET_KEY"):
                value = getattr(self, name).strip()
                if not value or value == type(self).model_fields[name].default:
                    raise ValueError(
                        f"{name} must be set to a non-default value in production"
                    )
        return self

settings = Settings()

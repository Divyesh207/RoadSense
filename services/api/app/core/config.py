
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "Road Intelligence & Pothole Management Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "default-insecure-secret-key-change-in-production-min-32-chars"

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    CORS_ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/road_platform"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/road_platform"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Authentication & Security
    JWT_SECRET: str = "default-insecure-jwt-secret-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

    # Supabase (Managed Postgres & Object Storage)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Storage Buckets
    SUPABASE_STORAGE_BUCKET_INSPECTION_MEDIA: str = "inspection-media"
    SUPABASE_STORAGE_BUCKET_REPAIR_EVIDENCE: str = "repair-evidence"
    SUPABASE_STORAGE_BUCKET_REPORTS: str = "reports"
    SUPABASE_STORAGE_BUCKET_MODEL_ARTIFACTS: str = "model-artifacts"

    # AI / ML
    AI_MODEL_DIR: str = "./data/models"
    YOLO_MODEL_PATH: str = "./data/models/pothole_yolov8.pt"
    AI_DEVICE: str = "cpu"
    AI_CONFIDENCE_THRESHOLD: float = 0.35
    AI_NMS_IOU_THRESHOLD: float = 0.45


settings = Settings()

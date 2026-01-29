import os
from dataclasses import dataclass
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables."""

    # MinIO Configuration
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket_insights: str
    minio_bucket_roteiros: str
    minio_bucket_aulas: str
    save_on_minio: bool
    wipe_bucket_before_start: bool

    # Gemini Configuration
    gemini_api_key: str
    gemini_model_name: str

    # OpenAI Configuration
    openai_host: str
    openai_model_name: str
    openai_api_key: str

    # AI Provider Selection ('gemini' or 'openai')
    ai_provider: str

    # Application Configuration
    app_name: str
    app_env: str
    log_level: str

    # Parallelism Configuration
    max_workers: int


@lru_cache(maxsize=1)
def get_config() -> Config:
    """
    Returns a singleton Config instance loaded from environment variables.

    Uses lru_cache to ensure configuration is loaded only once.
    """
    return Config(
        # MinIO
        minio_endpoint=os.getenv('MINIO_ENDPOINT', 'http://minio:9000'),
        minio_access_key=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        minio_secret_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        minio_bucket_insights=os.getenv('MINIO_BUCKET_NAME_INSIGHTS', 'insights'),
        minio_bucket_roteiros=os.getenv('MINIO_BUCKET_NAME_ROTEIROS', 'roteiros'),
        minio_bucket_aulas=os.getenv('MINIO_BUCKET_NAME', 'aulas-inclusao-digital'),
        save_on_minio=os.getenv('SAVE_ON_MINIO', 'true').lower() == 'true',
        wipe_bucket_before_start=os.getenv('WIPE_BUCKET_BEFORE_START', 'false').lower() == 'true',

        # Gemini
        gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
        gemini_model_name=os.getenv('GENAI_MODEL_NAME', 'gemini-2.5-flash'),

        # OpenAI
        openai_host=os.getenv('OPENAI_HOST', 'https://api.openai.com/v1'),
        openai_model_name=os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini'),
        openai_api_key=os.getenv('OPENAI_KEY', ''),

        # AI Provider
        ai_provider=os.getenv('AI_PROVIDER', 'gemini'),

        # Application
        app_name=os.getenv('APP_NAME', 'scraper-idosos'),
        app_env=os.getenv('APP_ENV', 'development'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),

        # Parallelism
        max_workers=int(os.getenv('MAX_WORKERS', '4')),
    )

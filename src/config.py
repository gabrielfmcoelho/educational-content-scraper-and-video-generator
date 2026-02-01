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
    minio_bucket_pilulas: str  # Knowledge pills JSON data
    minio_bucket_infograficos: str  # Pill infographic images
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

    # Veo Configuration
    veo_api_key: str
    veo_model_name: str
    use_vertex_ai: bool
    vertex_project: str
    vertex_location: str
    vertex_gcs_bucket: str  # GCS bucket for Vertex AI video output

    # Application Configuration
    app_name: str
    app_env: str
    log_level: str

    # Parallelism Configuration
    max_workers: int

    # Video Generation Flags
    skip_roteiro_generation: bool
    max_videos_per_run: int  # 0 = unlimited
    veo_extensions: int  # Number of times to extend video (~8s each)
    roteiro_num_scenes: int  # Number of scenes in each roteiro

    # Pill Generation Flags
    skip_pill_generation: bool
    max_pills_per_run: int  # 0 = unlimited


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
        minio_bucket_pilulas=os.getenv('MINIO_BUCKET_PILULAS', 'pilulas'),
        minio_bucket_infograficos=os.getenv('MINIO_BUCKET_INFOGRAFICOS', 'infograficos'),
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

        # Veo
        veo_api_key=os.getenv('VEO_API_KEY', ''),
        veo_model_name=os.getenv('VEO_MODEL_NAME', 'veo-2'),
        use_vertex_ai=os.getenv('VEO_USE_VERTEX_AI', 'false').lower() == 'true',
        vertex_project=os.getenv('VERTEX_PROJECT', ''),
        vertex_location=os.getenv('VERTEX_LOCATION', 'us-central1'),
        vertex_gcs_bucket=os.getenv('VERTEX_GCS_BUCKET', ''),

        # Application
        app_name=os.getenv('APP_NAME', 'scraper-idosos'),
        app_env=os.getenv('APP_ENV', 'development'),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),

        # Parallelism
        max_workers=int(os.getenv('MAX_WORKERS', '4')),

        # Video Generation Flags
        skip_roteiro_generation=os.getenv('SKIP_ROTEIRO_GENERATION', 'false').lower() == 'true',
        max_videos_per_run=int(os.getenv('MAX_VIDEOS_PER_RUN', '0')),  # 0 = unlimited
        veo_extensions=int(os.getenv('VEO_EXTENSIONS', '5')),  # ~8s each, 5 = ~48s total
        roteiro_num_scenes=int(os.getenv('ROTEIRO_NUM_SCENES', '6')),  # Number of scenes per roteiro

        # Pill Generation Flags
        skip_pill_generation=os.getenv('SKIP_PILL_GENERATION', 'false').lower() == 'true',
        max_pills_per_run=int(os.getenv('MAX_PILLS_PER_RUN', '0')),  # 0 = unlimited
    )

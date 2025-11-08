from supabase import create_client, Client
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List

'''
App settings and Supabase client initialization
'''

class Settings(BaseSettings):

    SUPABASE_URL: str = "your-supabase-url"
    SUPABASE_KEY: str = "your-supabase-key"

    CORS_ORIGINS: List[str] = ["http://localhost:8000"]
    DATA_TABLE_NAME: str = "observation_data"
    PREDICTION_TABLE_NAME: str = "model_predictions"

    ML_LOOKBACK_HOURS: int = 24     # ML model input.
    DATA_RESOLUTION_MINUTES: int = 10

    DATA_RETRIEVAL_HOURS: int = 48  # Lookback for new historical data
    BUFFER_HOURS: int = 1           # Safety buffer for fetching new data
    DEFAULT_REQUEST_HOURS: int = 48
    MAX_REQUEST_HOURS: int = 168

    GOAS_19_XRAY_LONG: str = "https://services.swpc.noaa.gov/json/goes/secondary/xrays-3-day.json"

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

if not all([settings.SUPABASE_URL, settings.SUPABASE_KEY]):
    raise ValueError("Supabase .env variables missing.")

# Initialize Supabase client
db: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


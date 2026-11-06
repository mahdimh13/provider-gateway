from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    app_name: str = 'provider-gateway'
    environment: str = 'development'
    database_url: str = 'postgresql+asyncpg://gateway:gateway@postgres:5432/gateway'
    redis_url: str = 'redis://redis:6379/0'
    celery_broker_url: str = 'amqp://guest:guest@rabbitmq:5672//'
    celery_result_backend: str = 'redis://redis:6379/1'
    provider_a_url: str = 'http://92.114.51.251:8001/v1/process'
    provider_b_url: str = 'http://92.114.51.251:8002/v1/process'
    provider_c_url: str = 'http://92.114.51.251:8003/v1/process'
    upstream_timeout_seconds: float = 12.0
    max_inflight_per_provider: int = 100
    service_rate_limit: int = 1000
    service_rate_window_seconds: int = 1
    circuit_failure_threshold: int = 5
    circuit_recovery_seconds: int = 20

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

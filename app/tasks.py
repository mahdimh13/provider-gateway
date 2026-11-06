import logging
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from .celery_app import celery
from .config import settings
from .models import RequestAudit

log = logging.getLogger(__name__)
# A synchronous driver is appropriate inside synchronous Celery workers.
sync_url = settings.database_url.replace('postgresql+asyncpg://', 'postgresql+psycopg://')
engine = create_engine(sync_url, pool_size=10, max_overflow=10, pool_pre_ping=True)

@celery.task(name='app.tasks.persist_audit', autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=8)
def persist_audit(event: dict):
    stmt = insert(RequestAudit).values(**event).on_conflict_do_nothing(index_elements=['request_id'])
    with engine.begin() as conn:
        conn.execute(stmt)

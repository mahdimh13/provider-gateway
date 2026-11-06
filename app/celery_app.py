from celery import Celery
from .config import settings
celery = Celery('gateway', broker=settings.celery_broker_url, backend=settings.celery_result_backend, include=['app.tasks'])
celery.conf.update(task_serializer='json', accept_content=['json'], result_serializer='json', task_acks_late=True, worker_prefetch_multiplier=1, task_reject_on_worker_lost=True, broker_connection_retry_on_startup=True)

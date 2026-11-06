import logging, time, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from redis.asyncio import Redis
from .config import settings
from .database import engine, Base
import app.models  # register ORM models before create_all
from .logging_config import configure_logging
from .metrics import REQUESTS, AUDIT_FAILURES
from .providers import provider_manager, ProviderUnavailable
from .rate_limit import enforce_rate_limit
from .schemas import ProcessRequest, ProcessResponse
from .tasks import persist_audit

configure_logging(); logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True, health_check_interval=30)
    await app.state.redis.ping()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await provider_manager.start()
    yield
    await provider_manager.close(); await app.state.redis.aclose(); await engine.dispose()

app = FastAPI(title='Provider Gateway', version='1.0.0', lifespan=lifespan)

@app.middleware('http')
async def trace_requests(request: Request, call_next):
    request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
    trace_id = request.headers.get('X-Trace-ID') or request_id
    request.state.request_id = request_id; request.state.trace_id = trace_id
    started = time.perf_counter()
    try: response = await call_next(request)
    except Exception:
        logger.exception('Unhandled request error', extra={'request_id': request_id, 'trace_id': trace_id})
        raise
    response.headers['X-Request-ID'] = request_id; response.headers['X-Trace-ID'] = trace_id
    response.headers['X-Process-Time-Ms'] = f'{(time.perf_counter()-started)*1000:.2f}'
    return response

@app.get('/health/live')
async def liveness(): return {'status': 'alive'}

@app.get('/health/ready')
async def readiness(request: Request):
    try: await request.app.state.redis.ping()
    except Exception: raise HTTPException(status_code=503, detail='Redis unavailable')
    return {'status': 'ready'}

@app.get('/metrics')
async def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.post('/v1/process', response_model=ProcessResponse)
async def process(body: ProcessRequest, request: Request, response: Response):
    request_id, trace_id = request.state.request_id, request.state.trace_id
    started = time.perf_counter(); provider = None; result = None; provider_status = None; error = None
    try:
        await enforce_rate_limit(request.app.state.redis)
        provider, provider_status, duration_ms, result = await provider_manager.process(body.payload, body.preferred_provider)
        status = 'success' if provider_status < 400 else 'upstream_client_error'
        REQUESTS.labels('/v1/process', status).inc()
        response.status_code = provider_status
        return ProcessResponse(request_id=request_id, trace_id=trace_id, provider=provider, provider_status=provider_status, duration_ms=round(duration_ms, 2), result=result)
    except ProviderUnavailable as exc:
        status = 'upstream_error'; error = str(exc); REQUESTS.labels('/v1/process', status).inc()
        raise HTTPException(status_code=503, detail={'message': error, 'request_id': request_id})
    except HTTPException as exc:
        status = 'rejected'; error = str(exc.detail); REQUESTS.labels('/v1/process', status).inc(); raise
    finally:
        # Celery/RabbitMQ decouples audit persistence from the response path.
        event = {'request_id': request_id, 'trace_id': trace_id, 'provider': provider, 'status': locals().get('status', 'failed'), 'http_status': provider_status, 'duration_ms': (time.perf_counter()-started)*1000, 'request_payload': body.payload, 'response_payload': result if isinstance(result, dict) else ({'value': result} if result is not None else None), 'error': error}
        try: persist_audit.apply_async(args=[event], queue='audit')
        except Exception: AUDIT_FAILURES.inc(); logger.exception('Could not enqueue audit event', extra={'request_id': request_id, 'trace_id': trace_id})

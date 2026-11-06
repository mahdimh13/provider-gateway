import asyncio, logging, time
from dataclasses import dataclass
from typing import Any
import httpx
from .config import settings
from .metrics import UPSTREAM, UPSTREAM_LATENCY, INFLIGHT

log = logging.getLogger(__name__)

@dataclass
class ProviderState:
    name: str
    url: str
    semaphore: asyncio.Semaphore
    failures: int = 0
    open_until: float = 0.0
    probe_lock: asyncio.Lock | None = None

class ProviderUnavailable(Exception): pass

class ProviderManager:
    def __init__(self):
        self.states = {
            'A': ProviderState('A', settings.provider_a_url, asyncio.Semaphore(settings.max_inflight_per_provider)),
            'B': ProviderState('B', settings.provider_b_url, asyncio.Semaphore(settings.max_inflight_per_provider)),
            'C': ProviderState('C', settings.provider_c_url, asyncio.Semaphore(settings.max_inflight_per_provider)),
        }
        self._next = 0
        self._lock = asyncio.Lock()
        self.client: httpx.AsyncClient | None = None

    async def start(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(settings.upstream_timeout_seconds, connect=2.0), limits=httpx.Limits(max_connections=500, max_keepalive_connections=100))

    async def close(self):
        if self.client: await self.client.aclose()

    async def _choose(self, preferred: str | None, excluded: set[str]) -> ProviderState:
        now = time.monotonic()
        if preferred:
            candidates = [self.states[preferred]] + [s for n,s in self.states.items() if n != preferred]
        else:
            async with self._lock:
                names = list(self.states)
                start = self._next % len(names); self._next += 1
                candidates = [self.states[names[(start+i) % len(names)]] for i in range(len(names))]
        for state in candidates:
            if state.name not in excluded and state.open_until <= now: return state
        raise ProviderUnavailable('All providers are temporarily unavailable')

    async def process(self, payload: dict[str, Any], preferred: str | None = None):
        if not self.client: raise RuntimeError('Provider manager not started')
        tried = set(); last_error = None
        # At most one attempt per provider: fail over on network/5xx/429, never retry indefinitely.
        for _ in range(3):
            try: state = await self._choose(preferred if not tried else None, tried)
            except ProviderUnavailable: break
            if state.name in tried: break
            tried.add(state.name)
            acquired = False
            try:
                await asyncio.wait_for(state.semaphore.acquire(), timeout=0.05); acquired = True
            except asyncio.TimeoutError:
                last_error = 'Provider concurrency limit reached'; continue
            started = time.perf_counter(); INFLIGHT.labels(state.name).inc()
            try:
                response = await self.client.post(state.url, json=payload)
                elapsed = time.perf_counter() - started
                UPSTREAM_LATENCY.labels(state.name).observe(elapsed)
                UPSTREAM.labels(state.name, str(response.status_code)).inc()
                if response.status_code < 500 and response.status_code != 429:
                    state.failures = 0; state.open_until = 0
                    try: result = response.json()
                    except ValueError: result = {'raw': response.text[:4000]}
                    return state.name, response.status_code, elapsed * 1000, result
                last_error = f'Provider {state.name} returned HTTP {response.status_code}'
                state.failures += 1
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                elapsed = time.perf_counter() - started
                UPSTREAM.labels(state.name, 'error').inc()
                last_error = f'{type(exc).__name__}: {str(exc)[:300]}'
                state.failures += 1
            finally:
                INFLIGHT.labels(state.name).dec()
                if acquired: state.semaphore.release()
            if state.failures >= settings.circuit_failure_threshold:
                state.open_until = time.monotonic() + settings.circuit_recovery_seconds
                log.warning('Circuit opened for provider %s', state.name)
        raise ProviderUnavailable(last_error or 'No healthy provider available')

provider_manager = ProviderManager()

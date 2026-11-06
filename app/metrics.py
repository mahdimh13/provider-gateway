from prometheus_client import Counter, Histogram, Gauge
REQUESTS = Counter('gateway_requests_total', 'Requests received', ['route', 'status'])
UPSTREAM = Counter('gateway_upstream_requests_total', 'Upstream requests', ['provider', 'status'])
UPSTREAM_LATENCY = Histogram('gateway_upstream_latency_seconds', 'Upstream latency', ['provider'], buckets=(.1,.3,.5,1,2,5,10,15))
INFLIGHT = Gauge('gateway_upstream_inflight', 'Current in-flight upstream calls', ['provider'])
AUDIT_FAILURES = Counter('gateway_audit_publish_failures_total', 'Audit publish failures')

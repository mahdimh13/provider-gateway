import json, logging, sys

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            'timestamp': self.formatTime(record), 'level': record.levelname,
            'logger': record.name, 'message': record.getMessage(),
        }
        for key in ('request_id', 'trace_id', 'provider', 'status_code', 'duration_ms'):
            value = getattr(record, key, None)
            if value is not None: payload[key] = value
        if record.exc_info: payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)

def configure_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear(); root.addHandler(handler); root.setLevel(logging.INFO)

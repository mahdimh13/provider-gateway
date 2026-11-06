FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install \
    --no-cache-dir \
    --retries 10 \
    --timeout 120 \
    --index-url https://package-mirror.liara.ir/repository/pypi/simple \
    -r requirements.txt

COPY app ./app
COPY tests ./tests

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
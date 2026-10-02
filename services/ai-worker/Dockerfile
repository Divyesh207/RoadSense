# syntax=docker/dockerfile:1
# Build context: ./services (see docker-compose.yml)
#
# The worker persists results through the API's SQLAlchemy domain package
# (services/api/app: ORM models, settings, spatial + storage helpers). It is
# copied in as the importable `app` package rather than duplicated in the repo.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /tmp/api-requirements.txt
COPY ai-worker/requirements.txt /tmp/worker-requirements.txt

# torch/torchvision come from the CPU-only index (default PyPI wheels bundle
# multi-GB CUDA libraries). The optional `extra_ca` BuildKit secret (see
# infrastructure/certs/README.md) supports HTTPS-intercepting networks; it is
# mounted only for this step and never stored in the image.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/ca-bundle.pem \
      && export PIP_CERT=/tmp/ca-bundle.pem; \
    fi \
    && pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu \
       "torch>=2.2.0,<3.0.0" "torchvision>=0.17.0,<1.0.0" \
    && pip install -r /tmp/api-requirements.txt -r /tmp/worker-requirements.txt \
    && rm -f /tmp/ca-bundle.pem

# Shared domain package from the API service
COPY api/app /app/app
# Worker code (worker/, inference/, pipelines/, preprocessing/, postprocessing/)
COPY ai-worker/ /app/

RUN useradd --create-home --uid 10001 worker && mkdir -p /app/models /data/media \
    && chown -R worker:worker /app /data
USER worker

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]

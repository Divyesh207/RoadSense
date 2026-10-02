# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Optional `extra_ca` BuildKit secret for HTTPS-intercepting networks
# (infrastructure/certs/README.md); mounted only for this step, never stored.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/extra_ca > /tmp/ca-bundle.pem \
      && export PIP_CERT=/tmp/ca-bundle.pem; \
    fi \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && rm -f /tmp/ca-bundle.pem

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

"""Settings parsing from environment variables."""

import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "raw",
    [
        "http://localhost:3000,http://localhost:8000",  # the form used in .env.example
        "http://localhost:3000, http://localhost:8000 ,",
        '["http://localhost:3000","http://localhost:8000"]',
    ],
)
def test_cors_origins_accept_comma_separated_and_json(monkeypatch, raw):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", raw)
    assert Settings(_env_file=None).CORS_ALLOWED_ORIGINS == ["http://localhost:3000", "http://localhost:8000"]

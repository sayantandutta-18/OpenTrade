"""Tests for security headers, rate limiting, and health checks."""

from __future__ import annotations

from fastapi.testclient import TestClient

from impactlab.api.main import app
from impactlab.api.rate_limiter import RateLimiter

client = TestClient(app)


def test_health_check_database_connectivity() -> None:
    """Test health check returns system and database status."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert "version" in data


def test_security_headers_present() -> None:
    """Test that all responses include strict security headers."""
    res = client.get("/api/v1/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"
    assert "max-age=" in res.headers.get("Strict-Transport-Security", "")


def test_rate_limiter_logic() -> None:
    """Test sliding window rate limiter unit behavior."""
    lim = RateLimiter(requests_per_minute=5, heavy_limit_per_minute=2)
    test_ip = "192.168.1.100"

    # 5 requests pass
    for _ in range(5):
        limited, _ = lim.is_rate_limited(test_ip, is_heavy=False)
        assert not limited

    # 6th request is limited
    limited, retry_after = lim.is_rate_limited(test_ip, is_heavy=False)
    assert limited
    assert retry_after > 0

    # Different IP is not limited
    other_limited, _ = lim.is_rate_limited("192.168.1.101", is_heavy=False)
    assert not other_limited

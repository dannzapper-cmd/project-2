from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.main import build_cors_middleware_options


def make_cors_client() -> TestClient:
    test_app = FastAPI()
    test_app.add_middleware(CORSMiddleware, **build_cors_middleware_options())

    @test_app.post("/v1/analyze/image")
    async def analyze_stub():
        return {"ok": True}

    return TestClient(test_app)


def preflight(client: TestClient, origin: str):
    return client.options(
        "/v1/analyze/image",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )


def test_cors_exact_allowed_origin(monkeypatch):
    origin = "https://snapinsight.example"
    monkeypatch.setenv("SNAPINSIGHT_ALLOWED_ORIGINS", origin)
    monkeypatch.delenv("SNAPINSIGHT_ALLOWED_ORIGIN_REGEX", raising=False)

    response = preflight(make_cors_client(), origin)

    assert response.headers["access-control-allow-origin"] == origin


def test_cors_preview_regex_allowed_when_configured(monkeypatch):
    preview_origin = "https://project-2-pr-123-dannzapper-1603s-projects.vercel.app"
    monkeypatch.setenv("SNAPINSIGHT_ALLOWED_ORIGINS", "https://snapinsight.example")
    monkeypatch.setenv(
        "SNAPINSIGHT_ALLOWED_ORIGIN_REGEX",
        r"^https://project-2-[a-z0-9-]+-dannzapper-1603s-projects\.vercel\.app$",
    )

    response = preflight(make_cors_client(), preview_origin)

    assert response.headers["access-control-allow-origin"] == preview_origin


def test_cors_unrelated_origin_is_not_allowed(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ALLOWED_ORIGINS", "https://snapinsight.example")
    monkeypatch.setenv(
        "SNAPINSIGHT_ALLOWED_ORIGIN_REGEX",
        r"^https://project-2-[a-z0-9-]+-dannzapper-1603s-projects\.vercel\.app$",
    )

    response = preflight(make_cors_client(), "https://project-2-evil.vercel.app")

    assert response.headers.get("access-control-allow-origin") is None


def test_cors_never_uses_wildcard_allow_origins(monkeypatch):
    monkeypatch.setenv("SNAPINSIGHT_ALLOWED_ORIGINS", "*")
    monkeypatch.delenv("SNAPINSIGHT_ALLOWED_ORIGIN_REGEX", raising=False)

    options = build_cors_middleware_options()
    response = preflight(make_cors_client(), "https://attacker.example")

    assert options["allow_origins"] != ["*"]
    assert "*" not in options["allow_origins"]
    assert response.headers.get("access-control-allow-origin") is None


def test_default_local_origins_include_loopback_hosts(monkeypatch):
    monkeypatch.delenv("SNAPINSIGHT_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("SNAPINSIGHT_ALLOWED_ORIGIN_REGEX", raising=False)

    options = build_cors_middleware_options()

    assert "http://localhost:3000" in options["allow_origins"]
    assert "http://127.0.0.1:3000" in options["allow_origins"]
    assert "*" not in options["allow_origins"]

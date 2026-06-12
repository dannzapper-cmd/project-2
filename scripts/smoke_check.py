#!/usr/bin/env python3
"""Lightweight SnapInsight smoke checks for local or deployed services.

The script avoids live Gemini/OpenFoodFacts calls and does not upload real images.
Set BACKEND_BASE_URL and optionally FRONTEND_URL, or pass --backend/--frontend.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 20
REQUEST_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
FORBIDDEN_RESPONSE_FRAGMENTS = (
    "gemini_api_key",
    "langfuse_secret_key",
    "snapinsight_live_access_code",
    "authorization",
    "api_key",
    "secret_key",
    "sk-lf",
    "aiza",
)


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    fatal: bool = False


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def _open_with_retries(request: urllib.request.Request):
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            return urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == REQUEST_ATTEMPTS:
                raise
            last_error = exc
        except (TimeoutError, urllib.error.URLError) as exc:
            if attempt == REQUEST_ATTEMPTS:
                raise
            last_error = exc
        time.sleep(RETRY_DELAY_SECONDS)
    if last_error:
        raise last_error
    raise RuntimeError("request retry loop exited unexpectedly")


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | None]:
    body = None
    headers: dict[str, str] = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    with _open_with_retries(request) as response:
        data = response.read()
        if not data:
            return response.status, None
        return response.status, json.loads(data.decode("utf-8"))


def _get_text(url: str) -> int:
    request = urllib.request.Request(url, method="GET")
    with _open_with_retries(request) as response:
        response.read(512)
        return response.status


def _contains_forbidden_fragment(body: dict[str, Any] | None) -> str | None:
    if body is None:
        return None
    serialized = json.dumps(body, sort_keys=True).lower()
    for fragment in FORBIDDEN_RESPONSE_FRAGMENTS:
        if fragment in serialized:
            return fragment
    return None


def _analysis_fixture(request_id: str, name: str, brand: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "mode": "mock",
        "status": "completed",
        "product": {
            "display_name": name,
            "category": "snack",
            "brand": brand,
            "detected_attributes": ["synthetic smoke fixture"],
            "confidence": {"score": 0.5, "label": "mock"},
            "barcode": None,
        },
        "insights": [],
        "warnings": ["Synthetic smoke fixture; no image was uploaded."],
        "citations": [
            {
                "source": "OpenFoodFacts",
                "title": name,
                "field": "nutriments",
                "field_label": "Nutrition",
                "value": "Energy 100.0kcal - Sugars 5.0g",
                "url": "https://world.openfoodfacts.org/product/smoke-fixture",
            }
        ],
        "next_questions": [],
        "privacy": {"image_stored": False, "image_retention": "none"},
        "meta": {"model": "mock", "latency_ms": 1, "api_version": "v1"},
        "grounding_status": "grounded",
        "grounding_summary": "Synthetic smoke fixture",
        "match_method": "none",
        "source_product_id": "smoke-fixture",
        "retrieved_at": None,
        "source_trace": ["smoke"],
        "product_enrichment": {
            "nutrition_summary": {
                "energy_kcal_100g": "100.0",
                "sugars_100g": "5.0",
                "fat_100g": None,
                "saturated_fat_100g": None,
                "proteins_100g": None,
                "salt_100g": None,
            },
            "nutrition_grade": None,
            "labels": [],
            "additives": [],
            "enrichment_source_confidence": "medium",
            "enrichment_notes": ["Synthetic smoke fixture."],
        },
        "cache_hit": None,
    }


def check_frontend(frontend_url: str | None) -> CheckResult:
    if not frontend_url:
        return CheckResult("frontend", "SKIP", "FRONTEND_URL not set")
    try:
        status = _get_text(frontend_url)
    except Exception as exc:  # noqa: BLE001
        return CheckResult("frontend", "FAIL", str(exc), fatal=True)
    if 200 <= status < 400:
        return CheckResult("frontend", "PASS", f"HTTP {status}")
    return CheckResult("frontend", "FAIL", f"HTTP {status}", fatal=True)


def check_health(backend_url: str) -> tuple[CheckResult, dict[str, Any] | None]:
    try:
        status, body = _request_json("GET", _url(backend_url, "/health"))
    except Exception as exc:  # noqa: BLE001
        return CheckResult("health", "FAIL", str(exc), fatal=True), None
    leaked = _contains_forbidden_fragment(body)
    if leaked:
        return CheckResult("health", "FAIL", f"forbidden field/value: {leaked}", fatal=True), body
    if status == 200 and body and body.get("status") == "ok":
        live_fields = [
            "gemini_live_enabled",
            "gemini_live_configured",
            "gemini_live_provider",
            "gemini_live_model",
        ]
        missing_live_fields = [field for field in live_fields if field not in body]
        if missing_live_fields:
            return CheckResult(
                "health",
                "FAIL",
                f"missing Live status fields: {', '.join(missing_live_fields)}",
                fatal=True,
            ), body
        mode = body.get("analysis_mode", body.get("mode", "unknown"))
        live = "enabled" if body.get("gemini_live_enabled") else "disabled"
        return CheckResult("health", "PASS", f"mode={mode}, live={live}"), body
    return CheckResult("health", "FAIL", f"HTTP {status}: {body}", fatal=True), body


def check_metrics(backend_url: str) -> tuple[CheckResult, dict[str, Any] | None]:
    try:
        status, body = _request_json("GET", _url(backend_url, "/v1/metrics/summary"))
    except Exception as exc:  # noqa: BLE001
        return CheckResult("metrics", "FAIL", str(exc), fatal=True), None
    leaked = _contains_forbidden_fragment(body)
    if leaked:
        return CheckResult("metrics", "FAIL", f"forbidden field/value: {leaked}", fatal=True), body
    if status == 200 and isinstance(body, dict) and "counters" in body:
        live_fields = [
            "gemini_live_enabled",
            "gemini_live_configured",
            "gemini_live_provider",
            "gemini_live_model",
        ]
        missing_live_fields = [field for field in live_fields if field not in body]
        if missing_live_fields:
            return CheckResult(
                "metrics",
                "FAIL",
                f"missing Live status fields: {', '.join(missing_live_fields)}",
                fatal=True,
            ), body
        usage_fields = [
            "usage_limits_storage",
            "usage_limits_daily_analysis_limit",
            "usage_limits_daily_cost_limit_usd",
            "usage_limits_max_analyses_per_session",
        ]
        missing_usage_fields = [field for field in usage_fields if field not in body]
        if missing_usage_fields:
            return CheckResult(
                "metrics",
                "FAIL",
                f"missing usage limit fields: {', '.join(missing_usage_fields)}",
                fatal=True,
            ), body
        if body.get("usage_limits_storage") != "in_memory":
            return CheckResult(
                "metrics",
                "FAIL",
                f"unexpected usage_limits_storage: {body.get('usage_limits_storage')}",
                fatal=True,
            ), body
        return CheckResult("metrics", "PASS", "summary counters, Live, and usage limits returned"), body
    return CheckResult("metrics", "FAIL", f"HTTP {status}: {body}", fatal=True), body


def check_live_config(backend_url: str) -> tuple[CheckResult, dict[str, Any] | None]:
    try:
        status, body = _request_json("GET", _url(backend_url, "/v1/live/config"))
    except Exception as exc:  # noqa: BLE001
        return CheckResult("live_config", "FAIL", str(exc), fatal=True), None
    leaked = _contains_forbidden_fragment(body)
    if leaked:
        return CheckResult("live_config", "FAIL", f"forbidden field/value: {leaked}", fatal=True), body
    if status != 200 or not body:
        return CheckResult("live_config", "FAIL", f"HTTP {status}: {body}", fatal=True), body
    live_status = body.get("status")
    if body.get("enabled") is False:
        if live_status == "disabled" and body.get("configured") is False:
            return CheckResult(
                "live_config",
                "PASS",
                "disabled-safe config returned",
            ), body
        return CheckResult(
            "live_config",
            "FAIL",
            f"disabled config not safe: {body}",
            fatal=True,
        ), body
    if live_status in {"ready", "not_configured"}:
        return CheckResult("live_config", "PASS", f"status={live_status}"), body
    return CheckResult("live_config", "FAIL", f"unexpected body: {body}", fatal=True), body


def check_analyze() -> CheckResult:
    return CheckResult(
        "analyze",
        "SKIP",
        "SKIP: analyze endpoint requires real image; see manual checklist.",
    )


def check_chat(backend_url: str, health_body: dict[str, Any] | None) -> CheckResult:
    if not health_body or health_body.get("analysis_mode") != "mock":
        return CheckResult(
            "chat",
            "SKIP",
            "mock chat smoke requires SNAPINSIGHT_ANALYSIS_MODE=mock",
        )
    payload = {
        "analysis": _analysis_fixture("smoke-chat-analysis", "Smoke Product", "Demo"),
        "messages": [],
        "question": "Which source fields are available?",
    }
    try:
        status, body = _request_json(
            "POST", _url(backend_url, "/v1/chat/product"), payload=payload
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("chat", "FAIL", str(exc), fatal=True)
    if status == 200 and body and body.get("answer") and body.get("request_id"):
        return CheckResult("chat", "PASS", "mock answer returned")
    return CheckResult("chat", "FAIL", f"HTTP {status}: {body}", fatal=True)


def check_compare(backend_url: str) -> CheckResult:
    payload = {
        "product_a": {
            "label": "A",
            "analysis": _analysis_fixture("smoke-compare-a", "Smoke Product A", "Demo"),
        },
        "product_b": {
            "label": "B",
            "analysis": _analysis_fixture("smoke-compare-b", "Smoke Product B", "Demo"),
        },
    }
    try:
        status, body = _request_json(
            "POST", _url(backend_url, "/v1/compare/products"), payload=payload
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("compare", "FAIL", str(exc), fatal=True)
    if status == 200 and body and body.get("differences") and body.get("request_id"):
        return CheckResult("compare", "PASS", "synthetic comparison returned")
    return CheckResult("compare", "FAIL", f"HTTP {status}: {body}", fatal=True)


def check_graph(backend_url: str) -> CheckResult:
    payload = {"analysis": _analysis_fixture("smoke-graph", "Smoke Product", "Demo")}
    try:
        status, body = _request_json(
            "POST", _url(backend_url, "/v1/graph/product"), payload=payload
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult("graph", "FAIL", str(exc), fatal=True)
    if (
        status == 200
        and body
        and isinstance(body.get("nodes"), list)
        and body.get("request_id")
    ):
        return CheckResult(
            "graph",
            "PASS",
            f"graph_backend={body.get('graph_backend', 'unknown')}",
        )
    return CheckResult("graph", "FAIL", f"HTTP {status}: {body}", fatal=True)


def check_cors_preflight(backend_url: str, origin: str | None) -> CheckResult:
    if not origin:
        return CheckResult("cors_preflight", "SKIP", "PREVIEW_ORIGIN/FRONTEND_URL not set")
    request = urllib.request.Request(
        _url(backend_url, "/v1/analyze/image"),
        method="OPTIONS",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
        },
    )
    try:
        with _open_with_retries(request) as response:
            response.read()
            status = response.status
            allowed_origin = response.headers.get("Access-Control-Allow-Origin")
    except urllib.error.HTTPError as exc:
        status = exc.code
        allowed_origin = exc.headers.get("Access-Control-Allow-Origin")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("cors_preflight", "FAIL", str(exc), fatal=True)

    if 200 <= status < 400 and allowed_origin == origin:
        return CheckResult("cors_preflight", "PASS", f"allowed origin {origin}")
    return CheckResult(
        "cors_preflight",
        "FAIL",
        f"HTTP {status}, Access-Control-Allow-Origin={allowed_origin!r}",
        fatal=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SnapInsight smoke checks.")
    parser.add_argument(
        "--backend",
        default=os.getenv("BACKEND_BASE_URL", DEFAULT_BACKEND_BASE_URL),
        help="Backend base URL. Defaults to BACKEND_BASE_URL or local backend.",
    )
    parser.add_argument(
        "--frontend",
        default=os.getenv("FRONTEND_URL"),
        help="Optional frontend URL. Defaults to FRONTEND_URL.",
    )
    parser.add_argument(
        "--origin",
        default=os.getenv("PREVIEW_ORIGIN") or os.getenv("FRONTEND_URL"),
        help="Optional Origin for CORS preflight. Defaults to PREVIEW_ORIGIN or FRONTEND_URL.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results: list[CheckResult] = []

    results.append(check_frontend(args.frontend))
    health_result, health_body = check_health(args.backend)
    results.append(health_result)
    if not health_result.fatal:
        metrics_result, _metrics_body = check_metrics(args.backend)
        live_config_result, _live_config_body = check_live_config(args.backend)
        results.append(metrics_result)
        results.append(live_config_result)
        results.append(check_analyze())
        results.append(check_chat(args.backend, health_body))
        results.append(check_compare(args.backend))
        results.append(check_graph(args.backend))
        results.append(check_cors_preflight(args.backend, args.origin))

    for result in results:
        if result.name == "analyze" and result.detail.startswith("SKIP:"):
            print(result.detail)
            continue
        print(f"{result.status}: {result.name} - {result.detail}")

    fatal_failures = [result for result in results if result.fatal]
    if fatal_failures:
        print(f"FAIL: {len(fatal_failures)} fatal smoke check(s)")
        return 1

    print("PASS: smoke checks completed without fatal failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

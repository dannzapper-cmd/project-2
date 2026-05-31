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
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_BACKEND_BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 10


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str
    fatal: bool = False


def _url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


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
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        data = response.read()
        if not data:
            return response.status, None
        return response.status, json.loads(data.decode("utf-8"))


def _get_text(url: str) -> int:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        response.read(512)
        return response.status


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
    if status == 200 and body and body.get("status") == "ok":
        mode = body.get("analysis_mode", body.get("mode", "unknown"))
        return CheckResult("health", "PASS", f"mode={mode}"), body
    return CheckResult("health", "FAIL", f"HTTP {status}: {body}", fatal=True), body


def check_metrics(backend_url: str) -> CheckResult:
    try:
        status, body = _request_json("GET", _url(backend_url, "/v1/metrics/summary"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return CheckResult(
                "metrics",
                "WARN",
                "rate limited -- endpoint exists but throttled",
            )
        return CheckResult("metrics", "FAIL", f"HTTP {exc.code}", fatal=True)
    except Exception as exc:  # noqa: BLE001
        return CheckResult("metrics", "FAIL", str(exc), fatal=True)
    if status == 200 and isinstance(body, dict) and "counters" in body:
        return CheckResult("metrics", "PASS", "summary counters returned")
    return CheckResult("metrics", "FAIL", f"HTTP {status}: {body}", fatal=True)


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results: list[CheckResult] = []

    results.append(check_frontend(args.frontend))
    health_result, health_body = check_health(args.backend)
    results.append(health_result)
    if not health_result.fatal:
        results.append(check_metrics(args.backend))
        results.append(check_analyze())
        results.append(check_chat(args.backend, health_body))
        results.append(check_compare(args.backend))

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

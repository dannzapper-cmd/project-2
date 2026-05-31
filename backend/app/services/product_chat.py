import asyncio
import time

from google import genai
from google.genai import types

from app.config import Settings
from app.schemas import (
    AnalyzeImageResponse,
    ChatMessage,
    Citation,
    ProductChatResponse,
)
from app.services.product_graph import graph_context_for_chat


CHAT_TIMEOUT_SECONDS = 30.0
MAX_CONTEXT_CHARS = 2500
MAX_QUESTION_CHARS = 400
MAX_HISTORY_MESSAGES = 6
MAX_HISTORY_CHARS = 200
INJECTION_PATTERNS = [
    "ignore previous",
    "ignore instructions",
    "forget previous",
    "new instructions",
    "system prompt",
    "you are now",
    "act as if",
]

CHAT_SYSTEM_INSTRUCTION = """
You are SnapInsight's product follow-up assistant.
Answer only using the provided product analysis, OpenFoodFacts citations, and
product enrichment context. Say when information is missing or uncertain.
Reference source fields when relevant. Do not make medical diagnoses, prescribe
health decisions, make absolute health claims, or call a product definitively
healthy or unhealthy. Never invent allergens, ingredients, additives, nutrition,
or certifications. Keep answers short and mobile-friendly.
Use cautious language such as "Based on the available label data",
"OpenFoodFacts lists", "This may be relevant if you avoid", and
"I do not have enough source data to confirm". Suggest practical next steps
such as verifying the physical label, taking a clearer front-label photo, or
showing the barcode.
"""


class ProductChatError(Exception):
    def __init__(
        self,
        *,
        error: str,
        message: str,
        status_code: int = 503,
        latency_ms: int = 0,
    ) -> None:
        super().__init__(message)
        self.error = error
        self.message = message
        self.status_code = status_code
        self.latency_ms = latency_ms


class GeminiChatError(Exception):
    pass


def _latency_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


def validate_question(question: str) -> str:
    trimmed = question.strip()[:MAX_QUESTION_CHARS]
    if not trimmed:
        raise ProductChatError(
            error="empty_question",
            message="Question is required.",
            status_code=400,
        )

    lowered = trimmed.lower()
    # Basic prompt injection guard. Full hardening in 14/15.
    if any(pattern in lowered for pattern in INJECTION_PATTERNS):
        raise ProductChatError(
            error="invalid_question",
            message="Question contains disallowed content.",
            status_code=400,
        )

    return trimmed


def _append_with_budget(parts: list[str], text: str, used: int) -> int:
    if not text:
        return used
    if used + len(text) > MAX_CONTEXT_CHARS:
        return used
    parts.append(text)
    return used + len(text)


def _nutrition_lines(analysis: AnalyzeImageResponse) -> list[str]:
    enrichment = analysis.product_enrichment
    summary = enrichment.nutrition_summary if enrichment else None
    if not summary:
        return []

    values = [
        ("Energy kcal/100g", summary.energy_kcal_100g),
        ("Sugars/100g", summary.sugars_100g),
        ("Fat/100g", summary.fat_100g),
        ("Saturated fat/100g", summary.saturated_fat_100g),
        ("Protein/100g", summary.proteins_100g),
        ("Salt/100g", summary.salt_100g),
    ]
    return [f"{label}: {value}" for label, value in values if value]


def build_compact_context(
    analysis: AnalyzeImageResponse, messages: list[ChatMessage]
) -> str:
    # Context budget: keep Gemini chat prompts small and avoid raw source data.
    parts: list[str] = []
    used = 0
    product = analysis.product

    used = _append_with_budget(
        parts,
        (
            f"Product: {product.display_name}; brand: {product.brand or 'unknown'}; "
            f"category: {product.category}; confidence: "
            f"{product.confidence.label} {product.confidence.score}; "
            f"mode: {analysis.mode}; warnings: {' | '.join(analysis.warnings[:3])}"
        ),
        used,
    )
    used = _append_with_budget(
        parts,
        (
            f"Grounding: {analysis.grounding_status}; "
            f"summary: {analysis.grounding_summary}; "
            f"match_method: {analysis.match_method or 'none'}"
        ),
        used,
    )

    citation_lines = []
    for citation in analysis.citations[:4]:
        value = citation.value[:300]
        citation_lines.append(
            f"{citation.field_label} ({citation.field}): {value}"
        )
    used = _append_with_budget(parts, "Citations: " + " | ".join(citation_lines), used)

    nutrition = _nutrition_lines(analysis)
    if nutrition:
        used = _append_with_budget(parts, "Nutrition: " + " | ".join(nutrition), used)

    enrichment = analysis.product_enrichment
    if enrichment:
        used = _append_with_budget(
            parts,
            (
                f"Nutrition grade: {enrichment.nutrition_grade or 'unknown'}; "
                f"labels: {', '.join(enrichment.labels[:3])}; "
                f"additives: {', '.join(enrichment.additives[:4])}"
            ),
            used,
        )
        used = _append_with_budget(
            parts,
            "Enrichment notes: " + " | ".join(enrichment.enrichment_notes[:2]),
            used,
        )

    history_lines = []
    for message in messages[-MAX_HISTORY_MESSAGES:]:
        history_lines.append(
            f"{message.role}: {message.content.strip()[:MAX_HISTORY_CHARS]}"
        )
    used = _append_with_budget(parts, "Recent chat: " + " | ".join(history_lines), used)

    # GraphRAG Lite: enrich chat with evidence paths from the product graph.
    graph_paths = graph_context_for_chat(analysis)
    if graph_paths:
        used = _append_with_budget(parts, graph_paths, used)

    return "\n".join(parts)


def _mock_answer(analysis: AnalyzeImageResponse, question: str) -> str:
    product_name = analysis.product.display_name
    if analysis.grounding_status in {"no_match", "grounding_unavailable"}:
        source_note = " Source data is limited, so verify the product label."
    else:
        source_note = " Use the OpenFoodFacts citations as supplementary context."
    return (
        f"Mock response for {product_name}: based on the current analysis, "
        f"check the visible label, ingredients, allergens, and nutrition fields "
        f"that are present before deciding. Question: {question}.{source_note}"
    )


async def _gemini_chat_answer(
    *, settings: Settings, compact_context: str, question: str
) -> str:
    if not settings.gemini_api_key:
        raise GeminiChatError("MissingGeminiApiKey")

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = (
            f"{CHAT_SYSTEM_INSTRUCTION}\n\n"
            f"Product context:\n{compact_context}\n\n"
            f"User question: {question}"
        )
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=[types.Part.from_text(text=prompt)],
                config=types.GenerateContentConfig(
                    max_output_tokens=512,
                    temperature=0.2,
                ),
            ),
            timeout=CHAT_TIMEOUT_SECONDS,
        )
        text = getattr(response, "text", None)
        if not text:
            raise GeminiChatError("EmptyGeminiResponse")
        return text.strip()
    except asyncio.TimeoutError as exc:
        raise GeminiChatError("TimeoutError") from exc
    except Exception as exc:
        raise GeminiChatError(exc.__class__.__name__) from exc


def _citation_fields_for_answer(answer: str) -> set[str]:
    lowered = answer.lower()
    fields: set[str] = set()
    if any(keyword in lowered for keyword in ["ingredient", "contains"]):
        fields.add("ingredients_text")
    if any(keyword in lowered for keyword in ["allergen", "contains"]):
        fields.add("allergens_tags")
    if any(
        keyword in lowered
        for keyword in [
            "energy",
            "calorie",
            "sugar",
            "fat",
            "protein",
            "salt",
            "nutri",
            "grade",
        ]
    ):
        fields.update({"nutriments", "nutrition_grades"})
    if any(keyword in lowered for keyword in ["label", "organic", "certified"]):
        fields.add("labels_tags")
    if "additive" in lowered:
        fields.add("additives_tags")
    return fields


def citations_used_for_answer(
    answer: str, citations: list[Citation]
) -> list[Citation]:
    # Deterministic citation matching, not LLM-selected.
    fields = _citation_fields_for_answer(answer)
    if not fields:
        return []
    return [citation for citation in citations if citation.field in fields]


async def answer_product_question(
    *,
    request_id: str,
    analysis: AnalyzeImageResponse,
    messages: list[ChatMessage],
    question: str,
    settings: Settings,
    started_at: float,
) -> ProductChatResponse:
    if analysis.mode == "error":  # type: ignore[comparison-overlap]
        raise ProductChatError(
            error="chat_unavailable_no_analysis",
            message=(
                "Chat requires a valid analysis result. Please analyze a product first."
            ),
            status_code=400,
            latency_ms=_latency_ms(started_at),
        )

    safe_question = validate_question(question)
    compact_context = build_compact_context(analysis, messages)
    warnings: list[str] = []

    if settings.analysis_mode == "mock":
        answer = _mock_answer(analysis, safe_question)
        citations_used = citations_used_for_answer(answer, analysis.citations)
        if not citations_used:
            warnings.append("No source citation available for that detail.")
        return ProductChatResponse(
            answer=answer,
            mode="mock",
            citations_used=citations_used,
            warnings=warnings,
            request_id=request_id,
            latency_ms=_latency_ms(started_at),
        )

    try:
        answer = await _gemini_chat_answer(
            settings=settings,
            compact_context=compact_context,
            question=safe_question,
        )
        mode = "gemini"
    except GeminiChatError:
        if not settings.mock_fallback_allowed:
            raise ProductChatError(
                error="gemini_chat_unavailable",
                message="Gemini chat failed and mock fallback is disabled.",
                status_code=503,
                latency_ms=_latency_ms(started_at),
            )
        answer = _mock_answer(analysis, safe_question)
        mode = "mock_fallback"
        warnings.append("Gemini chat unavailable. Showing mock response.")

    citations_used = citations_used_for_answer(answer, analysis.citations)
    if not citations_used:
        warnings.append("No source citation available for that detail.")

    return ProductChatResponse(
        answer=answer,
        mode=mode,
        citations_used=citations_used,
        warnings=warnings,
        request_id=request_id,
        latency_ms=_latency_ms(started_at),
    )

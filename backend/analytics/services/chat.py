import json
import os
import urllib.error
import urllib.request
from typing import Any

from analytics.services.dashboard import get_chat_context
from analytics.services.filters import FilterParams


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# System prompt — strictly scoped to the food waste analytics dashboard.
# Gemini must NEVER invent numbers. All values must come from the context.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """You are a food waste analytics assistant for an institutional kitchen waste management dashboard.

YOUR ONLY JOB:
- Answer questions about the data shown in the "Dashboard Context" section below.
- The context contains real data fetched from the database for the current filter period.

STRICT RULES (follow every single one, no exceptions):
1. ONLY use numbers, dates, device names, food names, and percentages that appear in the Dashboard Context.
   Do NOT invent, estimate, or extrapolate any values.
2. For any calculation (percentages, averages, ratios, comparisons), compute using ONLY the numbers in the context.
   Show the formula if helpful: e.g. "Rice: 382 / 1247 × 100 = 30.6%".
3. If the question cannot be answered from the context, reply EXACTLY:
   "This information is not available in the current dashboard data."
4. If the question is not about food waste, kitchen operations, waste scans, devices, meals, categories,
   anomalies, trends, or cost impact, reply EXACTLY:
   "This question is outside the scope of the waste analytics dashboard."
5. Do NOT suggest, guess, or say things like "typically" or "generally" — stick to the data.
6. Keep answers concise (3–6 sentences max). Use bullet points only when listing multiple items.
7. Never mention being an AI, never mention Gemini, never discuss your own capabilities.

DATA SCHEMA (so you understand the context fields):
- summary.total_waste: total kg of food wasted in the filtered period
- summary.total_scans: number of valid waste scan records
- summary.total_devices: number of active weighing devices
- summary.average_daily_waste: kg per active day
- summary.abnormal_days: days where waste exceeded 1.2× the daily average
- summary.co2_impact: estimated CO₂e impact in kg (total_waste × 1.75 kg CO₂e/kg food waste)
- summary.most_wasted_food: {name, value} — top food item by kg
- summary.peak_waste_meal: {name, value} — meal type with highest waste
- food_items: list of {name, value} — all food items ranked by kg
- waste_categories: list of {name, value} — waste type breakdown (Plate Waste, Production Waste, etc.)
- meals: list of {name, value} — waste per meal type (Breakfast, Lunch, Dinner, Snacks, Others)
- top_devices: list of {name, value} — device serial numbers ranked by kg waste
- trend: list of {date, value, spike} — daily waste with spike flag
- weekly_waste: list of {week, value, week_value, start_date, end_date}
- weekday_waste: list of {day, value} — Mon–Sun average waste
- insights.key_insights: auto-generated text insights from the data
- insights.recommended_actions: actionable recommendations from the data
"""


def _build_prompt(question: str, context: dict[str, Any]) -> str:
    # Serialize context compactly — exclude large trend arrays beyond 30 entries to stay within token limits
    compact_context = {
        "summary": context.get("summary"),
        "food_items": context.get("food_items"),
        "waste_categories": context.get("waste_categories"),
        "meals": context.get("meals"),
        "top_devices": context.get("top_devices"),
        "trend_summary": {
            "total_days": len(context.get("trend", [])),
            "spike_days": [p for p in context.get("trend", []) if p.get("spike")],
            "first_day": context["trend"][0] if context.get("trend") else None,
            "last_day": context["trend"][-1] if context.get("trend") else None,
        },
        "weekly_waste": context.get("weekly_waste"),
        "weekday_waste": context.get("weekday_waste"),
        "insights": context.get("insights"),
    }
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Dashboard Context:\n{json.dumps(compact_context, default=str, indent=2)}\n\n"
        f"User question: {question}"
    )


def _call_gemini(prompt: str) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,        # Low temperature — factual, not creative
            "topP": 0.8,
            "maxOutputTokens": 512,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ],
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return f"Gemini request failed: {exc.read().decode('utf-8', errors='ignore')}"
    except Exception as exc:
        return f"Gemini request failed: {exc}"

    candidates = data.get("candidates") or []
    if not candidates:
        return "Gemini returned no answer."

    # Check if the response was blocked
    finish_reason = candidates[0].get("finishReason", "")
    if finish_reason in ("SAFETY", "RECITATION"):
        return "This question is outside the scope of the waste analytics dashboard."

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [p.get("text", "") for p in parts if p.get("text")]
    return "\n".join(text_parts).strip() or "No answer returned."


def _gemini_answer(question: str, context: dict[str, Any]) -> str:
    if not GEMINI_API_KEY:
        return _local_fallback(question, context)
    prompt = _build_prompt(question, context)
    return _call_gemini(prompt)


def _local_fallback(question: str, context: dict[str, Any]) -> str:
    """Simple fallback when Gemini API key is not configured."""
    summary = context.get("summary") or {}
    lowered = question.lower()

    if "total waste" in lowered:
        return f"Total waste is {summary.get('total_waste', 0):.2f} kg for the current filters."
    if "scan" in lowered:
        return f"Total valid scans: {summary.get('total_scans', 0)}."
    if "average" in lowered:
        return f"Average daily waste: {summary.get('average_daily_waste', 0):.2f} kg."
    if "most wasted" in lowered or "top food" in lowered:
        top = summary.get("most_wasted_food")
        return f"{top['name']}: {top['value']:.2f} kg." if top else "No food item data available."
    if "meal" in lowered:
        top = summary.get("peak_waste_meal")
        return f"Peak waste meal: {top['name']} at {top['value']:.2f} kg." if top else "No meal data available."
    if "device" in lowered:
        devices = context.get("top_devices") or []
        return f"Top device: {devices[0]['name']} — {devices[0]['value']:.2f} kg." if devices else "No device data available."
    if "anomaly" in lowered or "spike" in lowered:
        return f"Abnormal days detected: {summary.get('abnormal_days', 0)}."
    if "cost" in lowered or "rupee" in lowered or "inr" in lowered or "co2" in lowered or "carbon" in lowered:
        return f"Total CO\u2082e is {summary.get('co2_impact', 0):.2f} kg (1.75 kg CO\u2082e per kg of food waste)."

    return (
        f"Dashboard snapshot — "
        f"Total waste: {summary.get('total_waste', 0):.2f} kg | "
        f"Scans: {summary.get('total_scans', 0)} | "
        f"Avg daily: {summary.get('average_daily_waste', 0):.2f} kg | "
        f"Abnormal days: {summary.get('abnormal_days', 0)}."
    )


def answer_dashboard_question(question: str, filters: FilterParams, provider: str = "gemini") -> dict[str, Any]:
    context = get_chat_context(filters)
    # Always use Gemini if key is set; fall back to local if not configured
    answer = _gemini_answer(question, context)
    actual_provider = "gemini" if GEMINI_API_KEY else "local"
    return {
        "provider": actual_provider,
        "answer": answer,
        "context_summary": context["summary"],
    }


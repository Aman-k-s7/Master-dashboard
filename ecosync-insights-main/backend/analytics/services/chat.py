import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from analytics.services.dashboard import get_chat_context
from analytics.services.filters import FilterParams


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FAQ_PATH = Path(__file__).resolve().parent.parent / "dashboard_faqs.json"


ALLOWED_KEYWORDS = {
    "waste",
    "food",
    "scan",
    "device",
    "meal",
    "breakfast",
    "lunch",
    "dinner",
    "snacks",
    "category",
    "trend",
    "anomaly",
    "week",
    "weekday",
    "co2",
    "carbon",
    "kg",
    "dashboard",
    "plate",
    "production",
    "preparation",
    "peak",
}


def _is_dashboard_question(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in ALLOWED_KEYWORDS)


def _load_faqs() -> list[dict[str, str]]:
    if not FAQ_PATH.exists():
        return []
    try:
        data = json.loads(FAQ_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("question")]


def _answer_from_intent(intent: str, context: dict[str, Any]) -> str | None:
    summary = context["summary"]
    food_items = context["food_items"]
    waste_categories = context["waste_categories"]
    meals = context["meals"]
    devices = context["top_devices"]
    trend = context["trend"]
    weekly_waste = context["weekly_waste"]

    if intent == "total_waste":
        return f"Total waste recorded is {summary['total_waste']:.2f} kg."
    if intent == "total_scans":
        return f"A total of {summary['total_scans']} scans have been recorded."
    if intent == "average_daily_waste":
        return f"The average daily waste is {summary['average_daily_waste']:.2f} kg per day."
    if intent == "most_wasted_food":
        top_food = summary.get("most_wasted_food")
        if top_food:
            return f"{top_food['name']} is the most wasted food item with {top_food['value']:.2f} kg."
        return "The dashboard does not show a most wasted food item for the current filters."
    if intent == "peak_waste_meal":
        peak_meal = summary.get("peak_waste_meal")
        if peak_meal:
            return f"{peak_meal['name']} generates the highest waste with {peak_meal['value']:.2f} kg."
        return "The dashboard does not show a peak waste meal for the current filters."
    if intent == "waste_category_breakdown":
        if not waste_categories:
            return "The dashboard does not show waste category data for the current filters."
        total = sum(float(item["value"]) for item in waste_categories) or 1
        parts = [
            f"{item['name']}: {((float(item['value']) / total) * 100):.2f}%"
            for item in waste_categories
        ]
        return "Waste is distributed as:\n" + "\n".join(parts)
    if intent == "waste_trend":
        if not trend:
            return "The dashboard does not show a waste trend for the current filters."
        first = trend[0]["value"]
        last = trend[-1]["value"]
        direction = "stable"
        if last > first * 1.05:
            direction = "increasing"
        elif last < first * 0.95:
            direction = "decreasing"
        peaks = [item["date"] for item in trend if item["spike"]][:5]
        peak_text = ", ".join(peaks) if peaks else "no major spike dates"
        return f"Waste shows a {direction} trend over time with peaks on {peak_text}."
    if intent == "anomaly_days":
        anomalies = [item["date"] for item in trend if item["spike"]][:10]
        if not anomalies:
            return "No unusual high-waste days were detected for the current filters."
        return "High waste was observed on:\n" + "\n".join(anomalies) + "\nThese are considered abnormal days."
    if intent == "current_week_total":
        if not weekly_waste:
            return "The dashboard does not show weekly waste for the current filters."
        current_week = weekly_waste[-1]
        return f"Total waste for the selected week ({current_week['week']}) is {current_week['value']:.2f} kg."
    if intent == "top_device":
        if not devices:
            return "The dashboard does not show any device waste data for the current filters."
        top_device = devices[0]
        return f"{top_device['name']} generated the highest waste with {top_device['value']:.2f} kg."
    return None


def _local_answer(question: str, context: dict[str, Any]) -> str:
    if not _is_dashboard_question(question):
        return "I can answer only dashboard-related questions about waste, scans, meals, categories, devices, CO2, trends, and anomalies."

    lowered = question.lower()
    for faq in _load_faqs():
        if faq["question"].strip().lower() == lowered.strip():
            intent = faq.get("intent")
            if intent:
                answer = _answer_from_intent(intent, context)
                if answer:
                    return answer

    summary = context["summary"]
    food_items = context["food_items"]
    waste_categories = context["waste_categories"]
    meals = context["meals"]
    devices = context["top_devices"]
    trend = context["trend"]
    insights = context["insights"]

    if "total waste" in lowered:
        return f"Total waste is {summary['total_waste']:.2f} kg for the current filters."
    if "total scans" in lowered or "how many scans" in lowered:
        return f"Total scans are {summary['total_scans']} for the current filters."
    if "average daily" in lowered:
        return f"Average daily waste is {summary['average_daily_waste']:.2f} kg."
    if "most wasted" in lowered or "highest waste food" in lowered:
        top_food = summary.get("most_wasted_food")
        if top_food:
            return f"The most wasted food is {top_food['name']} with {top_food['value']:.2f} kg."
    if "peak waste meal" in lowered or "highest waste meal" in lowered:
        peak_meal = summary.get("peak_waste_meal")
        if peak_meal:
            return f"The peak waste meal is {peak_meal['name']} with {peak_meal['value']:.2f} kg."
    if "device" in lowered and devices:
        top_device = devices[0]
        return f"The top waste device is {top_device['name']} with {top_device['value']:.2f} kg."
    if "category" in lowered and waste_categories:
        top_category = waste_categories[0]
        return f"The largest waste category is {top_category['name']} with {top_category['value']:.2f} kg."
    if "trend" in lowered and trend:
        first_day = trend[0]
        last_day = trend[-1]
        return f"The daily waste trend spans from {first_day['date']} to {last_day['date']}. Latest recorded waste is {last_day['value']:.2f} kg."
    if "anomaly" in lowered:
        return f"There are {summary['abnormal_days']} anomaly days in the current filtered range."
    if "co2" in lowered or "carbon" in lowered:
        return f"Total CO\u2082e is {summary['co2_impact']:.2f} kg (1.75 kg CO\u2082e per kg of food waste)."
    if "insight" in lowered and insights["key_insights"]:
        return insights["key_insights"][0]

    quick_facts = []
    if summary.get("most_wasted_food"):
        quick_facts.append(f"most wasted food: {summary['most_wasted_food']['name']}")
    if summary.get("peak_waste_meal"):
        quick_facts.append(f"peak meal: {summary['peak_waste_meal']['name']}")
    quick_facts.append(f"total waste: {summary['total_waste']:.2f} kg")
    quick_facts.append(f"total scans: {summary['total_scans']}")
    return "Here is the current dashboard snapshot: " + ", ".join(quick_facts) + "."


def _gemini_answer(question: str, context: dict[str, Any]) -> str:
    if not _is_dashboard_question(question):
        return "I can answer only dashboard-related questions about this waste analytics dashboard."
    if not GEMINI_API_KEY:
        return "Gemini is not configured yet. Add GEMINI_API_KEY to the backend environment to enable Gemini answers."

    prompt = (
        "You are a dashboard-only analytics assistant. "
        "Answer only from the provided dashboard context. "
        "If the answer is not in the context, say that the dashboard data does not show it. "
        "Keep answers concise.\n\n"
        f"Dashboard context:\n{json.dumps(context, default=str)}\n\n"
        f"User question: {question}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                ]
            }
        ]
    }
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover
        return f"Gemini request failed: {exc.read().decode('utf-8', errors='ignore')}"
    except Exception as exc:  # pragma: no cover
        return f"Gemini request failed: {exc}"

    candidates = data.get("candidates") or []
    if not candidates:
        return "Gemini returned no answer."
    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip() or "Gemini returned an empty answer."


def answer_dashboard_question(question: str, filters: FilterParams, provider: str = "local") -> dict[str, Any]:
    context = get_chat_context(filters)
    provider_name = provider if provider in {"local", "gemini"} else "local"
    if provider_name == "gemini":
        answer = _gemini_answer(question, context)
    else:
        answer = _local_answer(question, context)
    return {
        "provider": provider_name,
        "answer": answer,
        "context_summary": context["summary"],
    }


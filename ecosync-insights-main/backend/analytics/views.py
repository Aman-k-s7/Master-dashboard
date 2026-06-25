import json

from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from analytics.services.chat import answer_dashboard_question
from analytics.services.dashboard import (
    get_anomaly_days,
    get_bain_marie_analytics,
    get_daily_avg_by_category,
    get_daily_waste_trend,
    get_dashboard_summary,
    get_dashboard_insights,
    get_filter_options,
    get_moisture_data,
    get_reason_breakdown,
    get_top_devices,
    get_usage_analytics,
    get_waste_by_food_item,
    get_waste_by_meal,
    get_waste_by_weekday,
    get_weekday_comparison_grid,
    get_waste_by_category,
    get_weekly_waste,
    inspect_scans,
    mark_scan_invalid,
)
from analytics.services.filters import FilterParams, parse_filters


def _parse_request_filters(request: HttpRequest) -> FilterParams:
    return parse_filters(request.GET)


def _normalize_chat_filters(raw_filters: dict) -> dict:
    normalized = dict(raw_filters or {})
    if "dateFrom" in normalized and "date_from" not in normalized:
        normalized["date_from"] = normalized.get("dateFrom")
    if "dateTo" in normalized and "date_to" not in normalized:
        normalized["date_to"] = normalized.get("dateTo")
    if "mealTypes" in normalized and "meal_types" not in normalized:
        value = normalized.get("mealTypes")
        normalized["meal_types"] = ",".join(value) if isinstance(value, list) else value
    if "weeks" in normalized:
        value = normalized.get("weeks")
        if isinstance(value, list):
            normalized["weeks"] = ",".join(value)
    for key in ("devices", "categories"):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = ",".join(value)
    return normalized


def _invalid_filters_response(exc: ValidationError) -> JsonResponse:
    return JsonResponse({"errors": exc.message_dict if hasattr(exc, "message_dict") else exc.messages}, status=400)


def _database_error_response(exc: DatabaseError) -> JsonResponse:
    return JsonResponse(
        {
            "errors": [
                "Database query failed. Confirm the imported MySQL schema and the WASTE_* column/table settings.",
                str(exc),
            ]
        },
        status=500,
    )


@require_GET
def dashboard_summary(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_dashboard_summary(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@require_GET
def waste_by_category(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_waste_by_category(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def waste_by_food_item(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_waste_by_food_item(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def waste_by_meal(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_waste_by_meal(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def daily_waste_trend(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_daily_waste_trend(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def anomaly_days(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_anomaly_days(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def weekly_waste(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_weekly_waste(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def waste_by_weekday(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_waste_by_weekday(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def weekday_comparison_grid(request: HttpRequest) -> JsonResponse:
    try:
        filters = _parse_request_filters(request)
        weeks = [week.strip() for week in (request.GET.get("weeks") or "").split(",") if week.strip()]
        payload = get_weekday_comparison_grid(filters, weeks)
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@require_GET
def top_devices(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_top_devices(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def dashboard_insights(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_dashboard_insights(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@require_GET
def filter_options(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_filter_options()
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@csrf_exempt
@require_http_methods(["POST"])
def chat_query(request: HttpRequest) -> JsonResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"errors": ["Invalid JSON body."]}, status=400)

    question = (payload.get("question") or "").strip()
    provider = (payload.get("provider") or "local").strip().lower()
    if not question:
        return JsonResponse({"errors": ["Question is required."]}, status=400)

    try:
        filters = parse_filters(_normalize_chat_filters(payload.get("filters") or {}))
        answer = answer_dashboard_question(question, filters, provider=provider)
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)

    return JsonResponse(answer)


@require_GET
def reason_breakdown(request: HttpRequest) -> JsonResponse:
    try:
        filters = _parse_request_filters(request)
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    category = request.GET.get("category", "").strip()
    try:
        payload = get_reason_breakdown(filters, category=category)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def moisture_data(request: HttpRequest) -> JsonResponse:
    try:
        filters = _parse_request_filters(request)
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    limit = request.GET.get("limit")
    try:
        payload = get_moisture_data(filters, limit=int(limit) if limit and limit.isdigit() else 250)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def usage_analytics(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_usage_analytics(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@require_GET
def bain_marie_analytics(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_bain_marie_analytics(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@require_GET
def daily_avg_by_category(request: HttpRequest) -> JsonResponse:
    try:
        payload = get_daily_avg_by_category(_parse_request_filters(request))
    except ValidationError as exc:
        return _invalid_filters_response(exc)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload, safe=False)


@require_GET
def scan_inspect(request: HttpRequest) -> JsonResponse:
    """Inspect all scans for a device on a date — useful for identifying anomalous records.
    GET /api/scan-inspect?device=CFS02&date=2025-07-05
    """
    device = request.GET.get("device", "").strip()
    date = request.GET.get("date", "").strip()
    if not device or not date:
        return JsonResponse({"errors": ["'device' and 'date' query params are required."]}, status=400)
    try:
        payload = inspect_scans(device, date)
    except DatabaseError as exc:
        return _database_error_response(exc)
    return JsonResponse(payload)


@csrf_exempt
@require_http_methods(["POST"])
def mark_invalid(request: HttpRequest) -> JsonResponse:
    """Mark a scan record as is_valid=0 to exclude it from all dashboard queries.
    POST /api/mark-invalid  body: {"id": 12345}
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"errors": ["Invalid JSON body."]}, status=400)
    scan_id = payload.get("id")
    if not scan_id or not str(scan_id).isdigit():
        return JsonResponse({"errors": ["'id' must be a valid integer."]}, status=400)
    try:
        result = mark_scan_invalid(int(scan_id))
    except DatabaseError as exc:
        return _database_error_response(exc)
    if not result["success"]:
        return JsonResponse(result, status=404)
    return JsonResponse(result)

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from analytics.services.filters import FilterParams
from django.db import connection


SCAN_TABLE = os.getenv("WASTE_SCAN_TABLE", "scm_scans")
COMPANY_ID = int(os.getenv("WASTE_COMPANY_ID", "312"))
WEIGHT_MULTIPLIER = float(os.getenv("WASTE_WEIGHT_MULTIPLIER", "100"))
ABNORMAL_MULTIPLIER = float(os.getenv("WASTE_ABNORMAL_MULTIPLIER", "1.2"))
# FIXED_DEVICE_SERIAL removed - now supports all devices
FIXED_DEVICE_SERIAL = os.getenv("WASTE_FIXED_DEVICE_SERIAL", None)


def _table() -> str:
    return f"`{SCAN_TABLE}`"


def _json_value_expr(path: str) -> str:
    return (
        f"CASE WHEN JSON_VALID(request) "
        f"THEN JSON_UNQUOTE(JSON_EXTRACT(request, '{path}')) "
        f"ELSE NULL END"
    )


def _weight_expr() -> str:
    request_weight = _json_value_expr("$.scan_data.weight")
    return f"COALESCE(NULLIF(CAST({request_weight} AS DECIMAL(18, 3)), 0), COALESCE(weight, 0) * {WEIGHT_MULTIPLIER})"


def _meal_expr() -> str:
    return _json_value_expr("$.scan_data.day_part")


def _waste_type_expr() -> str:
    # Return raw DB value without any remapping so exact names like
    # "Bain Marie Waste" are preserved throughout the dashboard.
    return _json_value_expr("$.scan_data.food_waste_type")


def _amount_expr() -> str:
    request_amount = _json_value_expr("$.scan_data.amount")
    return f"COALESCE(CAST({request_amount} AS DECIMAL(18, 3)), COALESCE(amount, 0))"


def _where_clause(filters: FilterParams) -> tuple[str, list]:
    clauses = ["company_id = %s", "commodity_name IS NOT NULL", "created_on_date IS NOT NULL", "is_valid = 1"]
    params: list = [COMPANY_ID]

    if filters.date_from:
        clauses.append("created_on_date >= %s")
        params.append(filters.date_from)
    if filters.date_to:
        clauses.append("created_on_date <= %s")
        params.append(filters.date_to)
    if filters.devices:
        placeholders = ", ".join(["%s"] * len(filters.devices))
        clauses.append(f"device_serial_no IN ({placeholders})")
        params.extend(filters.devices)
    if filters.meal_types:
        placeholders = ", ".join(["%s"] * len(filters.meal_types))
        clauses.append(f"{_meal_expr()} IN ({placeholders})")
        params.extend(filters.meal_types)
    if filters.categories:
        placeholders = ", ".join(["%s"] * len(filters.categories))
        clauses.append(f"commodity_name IN ({placeholders})")
        params.extend(filters.categories)
    if filters.waste_types:
        placeholders = ", ".join(["%s"] * len(filters.waste_types))
        clauses.append(f"{_waste_type_expr()} IN ({placeholders})")
        params.extend(filters.waste_types)
    if filters.weeks:
        placeholders = ", ".join(["%s"] * len(filters.weeks))
        clauses.append(f"CONCAT(YEAR(created_on_date), '-W', LPAD(WEEK(created_on_date, 3), 2, '0')) IN ({placeholders})")
        params.extend(filters.weeks)
    return "WHERE " + " AND ".join(clauses), params


def _fetch_all(sql: str, params: list) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_one(sql: str, params: list) -> dict:
    rows = _fetch_all(sql, params)
    return rows[0] if rows else {}

    
def _iso_week_bounds(year_no: int, week_no: int) -> tuple[datetime.date, datetime.date]:
    week_start = datetime.fromisocalendar(int(year_no), int(week_no), 1).date()
    week_end = datetime.fromisocalendar(int(year_no), int(week_no), 7).date()
    return week_start, week_end


def _format_week_label(start_date, end_date) -> str:
    if start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return f"{start_date.strftime('%b %d')} - {end_date.strftime('%d, %Y')}"
        return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    return f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}"


def get_dashboard_summary(filters: FilterParams) -> dict:
    where_sql, params = _where_clause(filters)
    summary_sql = f"""
        SELECT
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS total_waste,
            COUNT(*) AS total_scans,
            COUNT(DISTINCT device_serial_no) AS total_devices,
            ROUND(COALESCE(SUM({_weight_expr()}), 0) * 1.75, 3) AS co2_impact
        FROM {_table()}
        {where_sql}
    """
    summary = _fetch_one(summary_sql, params)

    abnormal_sql = f"""
        SELECT COUNT(*) AS abnormal_days
        FROM (
            SELECT created_on_date, SUM({_weight_expr()}) AS daily_waste
            FROM {_table()}
            {where_sql}
            GROUP BY created_on_date
        ) AS daily_totals
        WHERE daily_waste > (
            SELECT COALESCE(AVG(daily_waste), 0) * %s
            FROM (
                SELECT created_on_date, SUM({_weight_expr()}) AS daily_waste
                FROM {_table()}
                {where_sql}
                GROUP BY created_on_date
            ) AS averages
        )
    """
    abnormal = _fetch_one(abnormal_sql, [*params, ABNORMAL_MULTIPLIER, *params])

    most_wasted_food = get_waste_by_food_item(filters, limit=1)
    peak_waste_meal = get_waste_by_meal(filters, limit=1)
    active_days_sql = f"""
        SELECT COUNT(*) AS active_days
        FROM (
            SELECT created_on_date, SUM({_weight_expr()}) AS daily_waste
            FROM {_table()}
            {where_sql}
            GROUP BY created_on_date
            HAVING SUM({_weight_expr()}) > 0
        ) AS active_days
    """
    active_days_row = _fetch_one(active_days_sql, params)
    total_waste = float(summary.get("total_waste") or 0)
    active_days = int(active_days_row.get("active_days") or 0)

    return {
        "total_waste": total_waste,
        "total_scans": int(summary.get("total_scans") or 0),
        "total_devices": int(summary.get("total_devices") or 0),
        "average_daily_waste": round(total_waste / active_days, 3) if active_days else 0,
        "abnormal_days": int(abnormal.get("abnormal_days") or 0),
        "cost_loss": 0.0,
        "co2_impact": float(summary.get("co2_impact") or 0),
        "most_wasted_food": most_wasted_food[0] if most_wasted_food else None,
        "peak_waste_meal": peak_waste_meal[0] if peak_waste_meal else None,
    }


def get_waste_by_food_item(filters: FilterParams, limit: int | None = None) -> list[dict]:
    where_sql, params = _where_clause(filters)
    limit_sql = ""
    if limit:
        limit_sql = "LIMIT %s"
        params = [*params, limit]

    sql = f"""
        SELECT
            commodity_name AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
        GROUP BY commodity_name
        ORDER BY value DESC, name ASC
        {limit_sql}
    """
    return _fetch_all(sql, params)


def get_waste_by_category(filters: FilterParams) -> list[dict]:
    where_sql, params = _where_clause(filters)
    sql = f"""
        SELECT
            {_waste_type_expr()} AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
          AND {_waste_type_expr()} IS NOT NULL
        GROUP BY {_waste_type_expr()}
        ORDER BY value DESC, name ASC
    """
    return _fetch_all(sql, params)


def get_waste_by_meal(filters: FilterParams, limit: int | None = None) -> list[dict]:
    where_sql, params = _where_clause(filters)
    limit_sql = ""
    if limit:
        limit_sql = "LIMIT %s"
        params = [*params, limit]

    sql = f"""
        SELECT
            {_meal_expr()} AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
          AND {_meal_expr()} IS NOT NULL
        GROUP BY {_meal_expr()}
        ORDER BY value DESC, name ASC
        {limit_sql}
    """
    return _fetch_all(sql, params)


def get_reason_breakdown(filters: FilterParams, category: str) -> list[dict]:
    where_sql, params = _where_clause(filters)
    if category:
        where_sql = f"{where_sql} AND commodity_name = %s"
        params.append(category)
    sql = f"""
        SELECT
            {_waste_type_expr()} AS reason,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
          AND {_waste_type_expr()} IS NOT NULL
        GROUP BY {_waste_type_expr()}
        ORDER BY value DESC, reason ASC
    """
    rows = _fetch_all(sql, params)
    total_value = sum(float(row["value"] or 0) for row in rows)
    if total_value == 0:
        return []
    return [
        {
            "reason": row["reason"],
            "percentage": round((float(row["value"] or 0) / total_value) * 100, 2),
        }
        for row in rows
    ]


def get_daily_waste_trend(filters: FilterParams) -> list[dict]:
    where_sql, params = _where_clause(filters)
    sql = f"""
        SELECT
            created_on_date AS date,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
        GROUP BY created_on_date
        ORDER BY created_on_date ASC
    """
    rows = _fetch_all(sql, params)
    if not rows:
        return []

    average_value = sum(float(row["value"] or 0) for row in rows) / len(rows)
    threshold = average_value * ABNORMAL_MULTIPLIER
    return [
        {
            "date": row["date"].isoformat(),
            "value": float(row["value"] or 0),
            "spike": float(row["value"] or 0) > threshold,
        }
        for row in rows
    ]


def get_anomaly_days(filters: FilterParams) -> list[dict]:
    return [
        {"date": row["date"], "value": row["value"]}
        for row in get_daily_waste_trend(filters)
        if row["spike"]
    ]


def get_weekly_waste(filters: FilterParams) -> list[dict]:
    where_sql, params = _where_clause(filters)
    sql = f"""
        SELECT
            YEAR(created_on_date) AS year_no,
            WEEK(created_on_date, 3) AS week_no,
            MIN(created_on_date) AS start_date,
            MAX(created_on_date) AS end_date,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
        GROUP BY YEAR(created_on_date), WEEK(created_on_date, 3)
        ORDER BY year_no ASC, week_no ASC
    """
    rows = _fetch_all(sql, params)
    weekly_rows = []
    for row in rows:
        week_start, week_end = _iso_week_bounds(row['year_no'], row['week_no'])
        weekly_rows.append(
            {
                "week": _format_week_label(week_start, week_end),
                "value": float(row["value"] or 0),
                "week_value": f"{row['year_no']}-W{int(row['week_no']):02d}",
                "start_date": week_start.isoformat(),
                "end_date": week_end.isoformat(),
            }
        )
    return weekly_rows


def get_waste_by_weekday(filters: FilterParams) -> list[dict]:
    where_sql, params = _where_clause(filters)
    sql = f"""
        SELECT
            WEEKDAY(created_on_date) AS weekday_index,
            DAYNAME(created_on_date) AS day_name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
        GROUP BY WEEKDAY(created_on_date), DAYNAME(created_on_date)
        ORDER BY weekday_index ASC
    """
    rows = _fetch_all(sql, params)
    short_names = {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun",
    }
    return [
        {"day": short_names.get(row["day_name"], row["day_name"]), "value": float(row["value"] or 0)}
        for row in rows
    ]


def get_weekday_comparison_grid(filters: FilterParams, weeks: list[str]) -> dict:
    selected_weeks = [week for week in weeks if week]
    if not selected_weeks:
        return {"weeks": [], "rows": []}

    where_sql, params = _where_clause(filters)
    placeholders = ", ".join(["%s"] * len(selected_weeks))
    sql = f"""
        SELECT
            YEAR(created_on_date) AS year_no,
            WEEK(created_on_date, 3) AS week_no,
            WEEKDAY(created_on_date) AS weekday_index,
            DAYNAME(created_on_date) AS day_name,
            MIN(created_on_date) AS start_date,
            MAX(created_on_date) AS end_date,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
          AND CONCAT(YEAR(created_on_date), '-W', LPAD(WEEK(created_on_date, 3), 2, '0')) IN ({placeholders})
        GROUP BY YEAR(created_on_date), WEEK(created_on_date, 3), WEEKDAY(created_on_date), DAYNAME(created_on_date)
        ORDER BY YEAR(created_on_date), WEEK(created_on_date, 3), WEEKDAY(created_on_date)
    """
    rows = _fetch_all(sql, [*params, *selected_weeks])

    week_meta: dict[str, dict] = {}
    day_values = {
        "Mon": {},
        "Tue": {},
        "Wed": {},
        "Thu": {},
        "Fri": {},
        "Sat": {},
        "Sun": {},
    }
    short_names = {
        "Monday": "Mon",
        "Tuesday": "Tue",
        "Wednesday": "Wed",
        "Thursday": "Thu",
        "Friday": "Fri",
        "Saturday": "Sat",
        "Sunday": "Sun",
    }

    for row in rows:
        week_value = f"{row['year_no']}-W{int(row['week_no']):02d}"
        week_start, week_end = _iso_week_bounds(row['year_no'], row['week_no'])
        week_meta[week_value] = {
            "value": week_value,
            "label": _format_week_label(week_start, week_end),
        }
        day_values[short_names[row["day_name"]]][week_value] = float(row["value"] or 0)

    ordered_weeks = [week_meta[week] for week in selected_weeks if week in week_meta]
    comparison_weeks = [week["value"] for week in ordered_weeks]

    grid_rows = []
    for day, values in day_values.items():
        latest_change_pct = None
        if len(comparison_weeks) >= 2:
            previous_value = values.get(comparison_weeks[-2], 0)
            latest_value = values.get(comparison_weeks[-1], 0)
            if previous_value:
                latest_change_pct = round(((latest_value - previous_value) / previous_value) * 100, 2)
            elif latest_value:
                latest_change_pct = 100.0
            else:
                latest_change_pct = 0.0

        grid_rows.append(
            {
                "day": day,
                "values": {week["value"]: values.get(week["value"], 0) for week in ordered_weeks},
                "latest_change_pct": latest_change_pct,
            }
        )

    return {"weeks": ordered_weeks, "rows": grid_rows}


def get_top_devices(filters: FilterParams, limit: int = 5) -> list[dict]:
    where_sql, params = _where_clause(filters)
    safe_limit = max(1, min(limit, 20))
    sql = f"""
        SELECT
            device_serial_no AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {where_sql}
          AND device_serial_no IS NOT NULL
          AND device_serial_no <> ''
        GROUP BY device_serial_no
        ORDER BY value DESC, name ASC
        LIMIT %s
    """
    return _fetch_all(sql, [*params, safe_limit])


def get_filter_options() -> dict:
    base_where = "WHERE company_id = %s AND created_on_date IS NOT NULL AND is_valid = 1"
    base_params: list = [COMPANY_ID]
    # Removed FIXED_DEVICE_SERIAL filter to allow all devices

    devices_sql = f"""
        SELECT DISTINCT device_serial_no AS value
        FROM {_table()}
        {base_where}
          AND device_serial_no IS NOT NULL
          AND device_serial_no <> ''
        ORDER BY value ASC
    """
    meals_sql = f"""
        SELECT DISTINCT {_meal_expr()} AS value
        FROM {_table()}
        {base_where}
          AND {_meal_expr()} IS NOT NULL
        ORDER BY value ASC
    """
    categories_sql = f"""
        SELECT DISTINCT commodity_name AS value
        FROM {_table()}
        {base_where}
          AND commodity_name IS NOT NULL
          AND commodity_name <> ''
        ORDER BY value ASC
    """
    range_sql = f"""
        SELECT MIN(created_on_date) AS min_date, MAX(created_on_date) AS max_date
        FROM {_table()}
        {base_where}
    """

    waste_types_sql = f"""
        SELECT DISTINCT {_waste_type_expr()} AS value
        FROM {_table()}
        {base_where}
          AND {_waste_type_expr()} IS NOT NULL
          AND {_waste_type_expr()} <> ''
        ORDER BY value ASC
    """

    devices = [row["value"] for row in _fetch_all(devices_sql, base_params)]
    meals = [row["value"] for row in _fetch_all(meals_sql, base_params)]
    categories = [row["value"] for row in _fetch_all(categories_sql, base_params)]
    waste_types = [row["value"] for row in _fetch_all(waste_types_sql, base_params)]
    date_range = _fetch_one(range_sql, base_params)
    # Get weeks for all devices instead of just FIXED_DEVICE_SERIAL
    weeks = get_weekly_waste(FilterParams())

    return {
        "devices": devices,
        "meal_types": meals,
        "categories": categories,
        "waste_types": waste_types,
        "weeks": [
            {
                "label": week["week"],
                "value": week["week_value"],
                "start_date": week["start_date"],
                "end_date": week["end_date"],
            }
            for week in weeks
        ],
        "min_date": date_range["min_date"].isoformat() if date_range.get("min_date") else None,
        "max_date": date_range["max_date"].isoformat() if date_range.get("max_date") else None,
    }


def get_moisture_data(filters: FilterParams, limit: int = 250) -> list[dict]:
    where_sql, params = _where_clause(filters)
    safe_limit = max(1, min(limit, 1000))
    sql = f"""
        SELECT
            sample_id,
            NULL AS moisture,
            NULL AS temperature,
            ROUND({_weight_expr()}, 3) AS weight
        FROM {_table()}
        {where_sql}
        ORDER BY created_on_date DESC, id DESC
        LIMIT %s
    """
    rows = _fetch_all(sql, [*params, safe_limit])
    return [
        {
            "sample_id": row["sample_id"],
            "moisture": None,
            "temperature": None,
            "weight": float(row["weight"]) if row["weight"] is not None else None,
        }
        for row in rows
    ]


def get_dashboard_insights(filters: FilterParams) -> dict:
    summary = get_dashboard_summary(filters)
    food_items = get_waste_by_food_item(filters, limit=5)
    meals = get_waste_by_meal(filters, limit=5)
    devices = get_top_devices(filters, limit=5)
    anomalies = get_anomaly_days(filters)
    weekday = get_waste_by_weekday(filters)

    total_waste = summary["total_waste"] or 0
    top_food = food_items[0] if food_items else None
    peak_meal = meals[0] if meals else None
    top_device = devices[0] if devices else None
    top_weekday = max(weekday, key=lambda item: item["value"]) if weekday else None
    weekday_only = [item for item in weekday if item["day"] not in {"Sat", "Sun"}]
    weekend_only = [item for item in weekday if item["day"] in {"Sat", "Sun"}]
    weekday_avg = sum(item["value"] for item in weekday_only) / len(weekday_only) if weekday_only else 0
    weekend_avg = sum(item["value"] for item in weekend_only) / len(weekend_only) if weekend_only else 0

    key_insights: list[str] = []
    recommended_actions: list[str] = []
    patterns: list[dict] = []

    if top_food and total_waste:
        top_food_share = round((top_food["value"] / total_waste) * 100, 1)
        key_insights.append(f"{top_food['name']} accounts for {top_food_share}% of total waste and is the largest contributor.")
        recommended_actions.append(f"Review production planning for {top_food['name']} first, because it is currently the biggest waste driver.")
        patterns.append({
            "icon": "🍽️",
            "text": f"{top_food['name']} is the leading waste item with {top_food['value']:.2f} kg in the selected period.",
        })

    if peak_meal:
        key_insights.append(f"{peak_meal['name']} is the peak waste meal with {peak_meal['value']:.2f} kg recorded.")
        recommended_actions.append(f"Reduce overproduction during {peak_meal['name']} service and monitor batch sizing more closely.")
        patterns.append({
            "icon": "⏰",
            "text": f"{peak_meal['name']} consistently shows the highest waste volume in the selected filters.",
        })

    if top_device:
        device_share = round((top_device["value"] / total_waste) * 100, 1) if total_waste else 0
        key_insights.append(f"Device {top_device['name']} contributes the most waste at {device_share}% of the total.")
        recommended_actions.append(f"Audit device {top_device['name']} for process issues, calibration drift, and operator behavior.")
        patterns.append({
            "icon": "📍",
            "text": f"Device {top_device['name']} is the highest-waste source with {top_device['value']:.2f} kg.",
        })

    if anomalies:
        key_insights.append(f"{len(anomalies)} anomaly days were detected where waste spiked above the normal range.")
        recommended_actions.append("Review anomaly days against events, menu changes, and staffing gaps to find root causes.")
        first_anomaly = anomalies[0]
        patterns.append({
            "icon": "⚠️",
            "text": f"Anomaly detection flagged {len(anomalies)} high-waste days; the first visible spike is {first_anomaly['date']} at {first_anomaly['value']:.2f} kg.",
        })

    if weekday_avg and weekend_avg:
        if weekday_avg > weekend_avg:
            change = round(((weekday_avg - weekend_avg) / weekday_avg) * 100, 1)
            key_insights.append(f"Weekend waste is {change}% lower than the weekday average, suggesting weekday production pressure.")
            recommended_actions.append("Use weekday-specific production targets instead of carrying the same preparation strategy across the whole week.")
        else:
            change = round(((weekend_avg - weekday_avg) / weekend_avg) * 100, 1)
            key_insights.append(f"Weekend waste is {change}% higher than the weekday average, which points to weekend planning inefficiency.")
            recommended_actions.append("Investigate weekend staffing, menu planning, and forecasting because waste is not dropping on weekends.")

    if top_weekday:
        patterns.append({
            "icon": "📅",
            "text": f"{top_weekday['day']} is currently the highest-waste weekday at {top_weekday['value']:.2f} kg.",
        })

    return {
        "patterns": patterns[:4],
        "key_insights": key_insights[:5],
        "recommended_actions": recommended_actions[:5],
    }


def get_chat_context(filters: FilterParams) -> dict:
    return {
        "summary": get_dashboard_summary(filters),
        "food_items": get_waste_by_food_item(filters, limit=10),
        "waste_categories": get_waste_by_category(filters),
        "meals": get_waste_by_meal(filters),
        "top_devices": get_top_devices(filters, limit=10),
        "trend": get_daily_waste_trend(filters),
        "weekly_waste": get_weekly_waste(filters),
        "weekday_waste": get_waste_by_weekday(filters),
        "insights": get_dashboard_insights(filters),
    }


def get_usage_analytics(filters: FilterParams) -> dict:
    where_sql, params = _where_clause(filters)

    summary_sql = f"""
        SELECT
            COUNT(*) AS total_scans,
            COUNT(DISTINCT device_serial_no) AS total_devices
        FROM {_table()}
        {where_sql}
    """
    summary_row = _fetch_one(summary_sql, params)

    active_days_sql = f"""
        SELECT COUNT(DISTINCT created_on_date) AS active_days
        FROM {_table()}
        {where_sql}
    """
    active_days_row = _fetch_one(active_days_sql, params)

    total_scans = int(summary_row.get("total_scans") or 0)
    active_days = int(active_days_row.get("active_days") or 0)
    scans_per_day = round(total_scans / active_days) if active_days else 0

    scans_by_meal_sql = f"""
        SELECT
            {_meal_expr()} AS name,
            COUNT(*) AS value
        FROM {_table()}
        {where_sql}
          AND {_meal_expr()} IS NOT NULL
        GROUP BY {_meal_expr()}
        ORDER BY value DESC, name ASC
    """
    scans_by_meal = _fetch_all(scans_by_meal_sql, params)

    scans_by_waste_type_sql = f"""
        SELECT
            {_waste_type_expr()} AS name,
            COUNT(*) AS value
        FROM {_table()}
        {where_sql}
          AND {_waste_type_expr()} IS NOT NULL
        GROUP BY {_waste_type_expr()}
        ORDER BY value DESC, name ASC
    """
    scans_by_waste_type = _fetch_all(scans_by_waste_type_sql, params)

    return {
        "total_scans": total_scans,
        "active_days": active_days,
        "scans_per_day": scans_per_day,
        "total_devices": int(summary_row.get("total_devices") or 0),
        "scans_by_meal": [{"name": r["name"], "value": int(r["value"] or 0)} for r in scans_by_meal],
        "scans_by_waste_type": [{"name": r["name"], "value": int(r["value"] or 0)} for r in scans_by_waste_type],
    }


def get_bain_marie_analytics(filters: FilterParams) -> dict:
    from dataclasses import replace as dc_replace
    # Strip waste_type filter so Bain Marie section always shows Bain Marie data
    base_filters = dc_replace(filters, waste_types=())
    where_sql, params = _where_clause(base_filters)
    bm_where = f"{where_sql} AND {_waste_type_expr()} = 'Bain Marie Waste'"

    kpi_sql = f"""
        SELECT
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS total_waste,
            COUNT(DISTINCT created_on_date) AS active_days,
            COUNT(*) AS total_scans
        FROM {_table()}
        {bm_where}
    """
    kpi_row = _fetch_one(kpi_sql, params)
    total_waste = float(kpi_row.get("total_waste") or 0)
    active_days = int(kpi_row.get("active_days") or 0)
    daily_avg = round(total_waste / active_days, 3) if active_days else 0.0

    food_sql = f"""
        SELECT
            commodity_name AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {bm_where}
          AND commodity_name IS NOT NULL
        GROUP BY commodity_name
        ORDER BY value DESC, name ASC
        LIMIT 10
    """
    top_food = _fetch_all(food_sql, params)

    meal_sql = f"""
        SELECT
            {_meal_expr()} AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {bm_where}
          AND {_meal_expr()} IS NOT NULL
        GROUP BY {_meal_expr()}
        ORDER BY value DESC, name ASC
    """
    by_meal = _fetch_all(meal_sql, params)

    trend_sql = f"""
        SELECT
            created_on_date AS date,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS value
        FROM {_table()}
        {bm_where}
        GROUP BY created_on_date
        ORDER BY created_on_date ASC
    """
    trend_rows = _fetch_all(trend_sql, params)

    return {
        "kpi": {
            "total_waste": total_waste,
            "daily_average": daily_avg,
            "active_days": active_days,
        },
        "top_food_items": [{"name": r["name"], "value": float(r["value"] or 0)} for r in top_food],
        "by_meal": [{"name": r["name"], "value": float(r["value"] or 0)} for r in by_meal],
        "daily_trend": [{"date": r["date"].isoformat(), "value": float(r["value"] or 0)} for r in trend_rows],
    }


def get_daily_avg_by_category(filters: FilterParams) -> list[dict]:
    where_sql, params = _where_clause(filters)

    active_days_sql = f"""
        SELECT COUNT(DISTINCT created_on_date) AS active_days
        FROM {_table()}
        {where_sql}
    """
    active_days_row = _fetch_one(active_days_sql, params)
    active_days = int(active_days_row.get("active_days") or 0)
    if not active_days:
        return []

    sql = f"""
        SELECT
            commodity_name AS name,
            ROUND(COALESCE(SUM({_weight_expr()}), 0), 3) AS total
        FROM {_table()}
        {where_sql}
          AND commodity_name IS NOT NULL
          AND commodity_name <> ''
        GROUP BY commodity_name
        ORDER BY total DESC, name ASC
    """
    rows = _fetch_all(sql, params)
    return [
        {
            "name": r["name"],
            "value": round(float(r["total"] or 0) / active_days, 3),
        }
        for r in rows
    ]


def inspect_scans(device: str, date: str) -> dict:
    """Return all scans for a device+date with raw and computed weights for debugging."""
    json_w = (
        "CASE WHEN JSON_VALID(request) "
        "THEN JSON_UNQUOTE(JSON_EXTRACT(request, '$.scan_data.weight')) "
        "ELSE NULL END"
    )
    computed = f"COALESCE(NULLIF(CAST({json_w} AS DECIMAL(18,3)), 0), COALESCE(weight, 0) * {WEIGHT_MULTIPLIER})"
    sql = f"""
        SELECT
            id,
            commodity_name,
            weight                              AS raw_weight_col,
            {json_w}                            AS json_weight,
            ROUND({computed}, 3)                AS computed_weight_kg,
            is_valid,
            created_on_date
        FROM {_table()}
        WHERE company_id = %s
          AND device_serial_no = %s
          AND created_on_date = %s
        ORDER BY computed_weight_kg DESC, id ASC
    """
    rows = _fetch_all(sql, [COMPANY_ID, device, date])

    nearby_devices_sql = f"""
        SELECT DISTINCT device_serial_no, created_on_date, COUNT(*) AS scan_count
        FROM {_table()}
        WHERE company_id = %s
          AND created_on_date BETWEEN DATE_SUB(%s, INTERVAL 3 DAY) AND DATE_ADD(%s, INTERVAL 3 DAY)
        GROUP BY device_serial_no, created_on_date
        ORDER BY created_on_date ASC, scan_count DESC
        LIMIT 30
    """
    nearby = _fetch_all(nearby_devices_sql, [COMPANY_ID, date, date])

    device_dates_sql = f"""
        SELECT DISTINCT created_on_date, COUNT(*) AS scan_count
        FROM {_table()}
        WHERE company_id = %s
          AND device_serial_no = %s
        ORDER BY created_on_date DESC
        LIMIT 10
    """
    device_dates = _fetch_all(device_dates_sql, [COMPANY_ID, device])

    return {
        "query": {"company_id": COMPANY_ID, "table": SCAN_TABLE, "device": device, "date": date},
        "records": [
            {
                "id": row["id"],
                "commodity_name": row["commodity_name"],
                "raw_weight_col": float(row["raw_weight_col"] or 0),
                "json_weight": row["json_weight"],
                "computed_weight_kg": float(row["computed_weight_kg"] or 0),
                "is_valid": row["is_valid"],
                "created_on_date": row["created_on_date"].isoformat() if row["created_on_date"] else None,
            }
            for row in rows
        ],
        "debug": {
            "devices_near_date": [
                {
                    "device_serial_no": r["device_serial_no"],
                    "created_on_date": r["created_on_date"].isoformat() if r["created_on_date"] else None,
                    "scan_count": int(r["scan_count"]),
                }
                for r in nearby
            ],
            "recent_dates_for_device": [
                {
                    "created_on_date": r["created_on_date"].isoformat() if r["created_on_date"] else None,
                    "scan_count": int(r["scan_count"]),
                }
                for r in device_dates
            ],
        },
    }


def mark_scan_invalid(scan_id: int) -> dict:
    """Mark a single scan record as is_valid=0 to exclude it from all dashboard queries."""
    check_sql = f"SELECT id FROM {_table()} WHERE id = %s AND company_id = %s"
    rows = _fetch_all(check_sql, [scan_id, COMPANY_ID])
    if not rows:
        return {"success": False, "error": "Record not found or does not belong to this company."}
    update_sql = f"UPDATE {_table()} SET is_valid = 0 WHERE id = %s AND company_id = %s"
    with connection.cursor() as cursor:
        cursor.execute(update_sql, [scan_id, COMPANY_ID])
    return {"success": True, "id": scan_id, "message": f"Scan {scan_id} marked as invalid and excluded from dashboard."}


def mark_scans_invalid_by_date_weight(date: str, weight: float) -> dict:
    """Mark all scans on a given `date` whose computed weight (rounded to 3dp)
    equals `weight` as invalid (is_valid = 0). Returns the list of affected ids
    and a success flag. This is intended to remove anomalous scans such as the
    reported 80.08 kg entry on 5th May.

    Use with caution: this will permanently mark records as invalid for the
    configured `COMPANY_ID`.
    """
    rounded_weight = round(float(weight), 3)
    # Find matching records first
    sel_sql = f"""
        SELECT id, ROUND({_weight_expr()}, 3) AS computed_weight
        FROM {_table()}
        WHERE company_id = %s
          AND created_on_date = %s
          AND ROUND({_weight_expr()}, 3) = %s
    """
    rows = _fetch_all(sel_sql, [COMPANY_ID, date, rounded_weight])
    if not rows:
        return {"success": False, "error": "No matching scans found for the given date and weight."}

    ids = [r["id"] for r in rows]
    placeholders = ", ".join(["%s"] * len(ids))
    update_sql = f"UPDATE {_table()} SET is_valid = 0 WHERE id IN ({placeholders}) AND company_id = %s"
    with connection.cursor() as cursor:
        cursor.execute(update_sql, [*ids, COMPANY_ID])

    return {"success": True, "updated_count": len(ids), "ids": ids, "message": f"Marked {len(ids)} scan(s) invalid."}


def mark_scans_invalid_by_local_date_weight(local_date: str, weight: float, tz_name: str = "Asia/Kolkata") -> dict:
    """Mark scans within the local date (in timezone `tz_name`) whose computed
    weight (rounded to 3 dp) equals `weight` as invalid.

    This finds rows by `created_at` between the UTC range corresponding to the
    local date and updates `is_valid = 0` for matching records for `COMPANY_ID`.
    """
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return {"success": False, "error": f"Unknown timezone: {tz_name}"}

    try:
        local_start = datetime.strptime(local_date, "%Y-%m-%d").replace(tzinfo=tz)
    except Exception:
        return {"success": False, "error": "local_date must be in YYYY-MM-DD format"}

    local_end = local_start + timedelta(days=1)
    utc_start = local_start.astimezone(ZoneInfo("UTC"))
    utc_end = local_end.astimezone(ZoneInfo("UTC"))

    rounded_weight = round(float(weight), 3)

    sel_sql = f"""
        SELECT id, ROUND({_weight_expr()}, 3) AS computed_weight
        FROM {_table()}
        WHERE company_id = %s
          AND created_at >= %s
          AND created_at < %s
          AND ROUND({_weight_expr()}, 3) = %s
    """
    rows = _fetch_all(sel_sql, [COMPANY_ID, utc_start, utc_end, rounded_weight])
    if not rows:
        return {"success": False, "error": "No matching scans found for the given local date, timezone and weight."}

    ids = [r["id"] for r in rows]
    placeholders = ", ".join(["%s"] * len(ids))
    update_sql = f"UPDATE {_table()} SET is_valid = 0 WHERE id IN ({placeholders}) AND company_id = %s"
    with connection.cursor() as cursor:
        cursor.execute(update_sql, [*ids, COMPANY_ID])

    return {
        "success": True,
        "updated_count": len(ids),
        "ids": ids,
        "message": f"Marked {len(ids)} scan(s) invalid for local date {local_date} ({tz_name}).",
        "utc_range": {"start": utc_start.isoformat(), "end": utc_end.isoformat()},
    }

from django.urls import path

from analytics import views


urlpatterns = [
    path("dashboard-summary", views.dashboard_summary, name="dashboard-summary"),
    path("waste-by-food-item", views.waste_by_food_item, name="waste-by-food-item"),
    path("waste-by-category", views.waste_by_category, name="waste-by-category"),
    path("waste-by-meal", views.waste_by_meal, name="waste-by-meal"),
    path("reason-breakdown", views.reason_breakdown, name="reason-breakdown"),
    path("daily-waste-trend", views.daily_waste_trend, name="daily-waste-trend"),
    path("anomaly-days", views.anomaly_days, name="anomaly-days"),
    path("weekly-waste", views.weekly_waste, name="weekly-waste"),
    path("waste-by-weekday", views.waste_by_weekday, name="waste-by-weekday"),
    path("weekday-comparison-grid", views.weekday_comparison_grid, name="weekday-comparison-grid"),
    path("top-devices", views.top_devices, name="top-devices"),
    path("dashboard-insights", views.dashboard_insights, name="dashboard-insights"),
    path("filter-options", views.filter_options, name="filter-options"),
    path("chat-query", views.chat_query, name="chat-query"),
    path("moisture-data", views.moisture_data, name="moisture-data"),
    path("usage-analytics", views.usage_analytics, name="usage-analytics"),
    path("bain-marie-analytics", views.bain_marie_analytics, name="bain-marie-analytics"),
    path("daily-avg-by-category", views.daily_avg_by_category, name="daily-avg-by-category"),
    path("scan-inspect", views.scan_inspect, name="scan-inspect"),
    path("mark-invalid", views.mark_invalid, name="mark-invalid"),
    path("debug-scan-count", views.debug_scan_count, name="debug-scan-count"),
]

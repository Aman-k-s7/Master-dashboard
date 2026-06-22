import { useQueries, useQuery } from "@tanstack/react-query";

import { dashboardApi, type BainMarieAnalytics, type DashboardFilters, type UsageAnalytics } from "@/lib/dashboard";


export function useDashboardFilterOptions() {
  return useQuery({
    queryKey: ["dashboard-filter-options"],
    queryFn: dashboardApi.getFilterOptions,
  });
}


export function useDashboardData(filters: DashboardFilters) {
  const results = useQueries({
    queries: [
      { queryKey: ["dashboard-summary", filters], queryFn: () => dashboardApi.getSummary(filters) },
      { queryKey: ["dashboard-food-items", filters], queryFn: () => dashboardApi.getFoodItems(filters) },
      { queryKey: ["dashboard-waste-categories", filters], queryFn: () => dashboardApi.getWasteCategories(filters) },
      { queryKey: ["dashboard-meals", filters], queryFn: () => dashboardApi.getMeals(filters) },
      { queryKey: ["dashboard-trend", filters], queryFn: () => dashboardApi.getTrend(filters) },
      { queryKey: ["dashboard-anomalies", filters], queryFn: () => dashboardApi.getAnomalies(filters) },
      { queryKey: ["dashboard-weekly", filters], queryFn: () => dashboardApi.getWeeklyWaste(filters) },
      { queryKey: ["dashboard-weekday", filters], queryFn: () => dashboardApi.getWeekdayWaste(filters) },
      { queryKey: ["dashboard-top-devices", filters], queryFn: () => dashboardApi.getTopDevices(filters) },
      { queryKey: ["dashboard-insights", filters], queryFn: () => dashboardApi.getInsights(filters) },
      { queryKey: ["dashboard-usage-analytics", filters], queryFn: () => dashboardApi.getUsageAnalytics(filters) },
      { queryKey: ["dashboard-bain-marie", filters], queryFn: () => dashboardApi.getBainMarieAnalytics(filters) },
      { queryKey: ["dashboard-daily-avg-category", filters], queryFn: () => dashboardApi.getDailyAvgByCategory(filters) },
    ],
  });

  const [summary, foodItems, wasteCategories, meals, trend, anomalies, weeklyWaste, weekdayWaste, topDevices, insights, usageAnalytics, bainMarieAnalytics, dailyAvgByCategory] = results;
  return {
    summary: summary.data,
    foodItems: foodItems.data ?? [],
    wasteCategories: wasteCategories.data ?? [],
    meals: meals.data ?? [],
    trend: trend.data ?? [],
    anomalies: anomalies.data ?? [],
    weeklyWaste: weeklyWaste.data ?? [],
    weekdayWaste: weekdayWaste.data ?? [],
    topDevices: topDevices.data ?? [],
    insights: insights.data,
    usageAnalytics: usageAnalytics.data as UsageAnalytics | undefined,
    bainMarieAnalytics: bainMarieAnalytics.data as BainMarieAnalytics | undefined,
    dailyAvgByCategory: dailyAvgByCategory.data ?? [],
    isLoading: results.some((result) => result.isLoading),
    isError: results.some((result) => result.isError),
    error: (results.find((result) => result.error)?.error as Error | undefined) ?? undefined,
  };
}

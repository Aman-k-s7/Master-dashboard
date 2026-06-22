export interface DashboardFilters {
  dateFrom?: string;
  dateTo?: string;
  devices: string[];
  mealTypes: string[];
  categories: string[];
  wasteTypes: string[];
  weeks: string[];
}

export interface DashboardSummary {
  total_waste: number;
  total_scans: number;
  total_devices: number;
  average_daily_waste: number;
  abnormal_days: number;
  cost_loss: number;
  co2_impact: number;
  most_wasted_food: { name: string; value: number } | null;
  peak_waste_meal: { name: string; value: number } | null;
}

export interface NamedValue {
  name: string;
  value: number;
}

export interface TrendPoint {
  date: string;
  value: number;
  spike: boolean;
}

export interface WeekPoint {
  week: string;
  value: number;
  week_value: string;
  start_date: string;
  end_date: string;
}

export interface WeekdayPoint {
  day: string;
  value: number;
}

export interface FilterWeek {
  label: string;
  value: string;
  start_date: string;
  end_date: string;
}

export interface FilterOptions {
  devices: string[];
  meal_types: string[];
  categories: string[];
  waste_types: string[];
  weeks: FilterWeek[];
  min_date: string | null;
  max_date: string | null;
}

export interface DashboardInsights {
  patterns: Array<{ icon: string; text: string }>;
  key_insights: string[];
  recommended_actions: string[];
}

export interface WeekdayComparisonGrid {
  weeks: Array<{ value: string; label: string }>;
  rows: Array<{
    day: string;
    values: Record<string, number>;
    latest_change_pct: number | null;
  }>;
}


export interface UsageAnalytics {
  total_scans: number;
  active_days: number;
  scans_per_day: number;
  total_devices: number;
  scans_by_meal: Array<{ name: string; value: number }>;
  scans_by_waste_type: Array<{ name: string; value: number }>;
}


export interface BainMarieAnalytics {
  kpi: { total_waste: number; daily_average: number; active_days: number };
  top_food_items: Array<{ name: string; value: number }>;
  by_meal: Array<{ name: string; value: number }>;
  daily_trend: Array<{ date: string; value: number }>;
}


export const DEVICE_DISPLAY_NAMES: Record<string, string> = {
  "CFS01": "CPU (Gurgaon)",
  "AGFW26008": "CPU (Hyderabad)",
  "AGFW26016": "Flames University (Pune)",
  "CFS02": "Cafe Ananda (Gurgaon)",
  "AGFW26006": "CPU 3 BLR WHITEFIELD (Bangalore)",
  "AGFW26010": "Morgan Stanley (Mumbai)",
  "AGFW26011": "GE India (Pune)",
  "CFSO13": "Morgan Stanley (Mumbai)",
  "AGFW26009": "APOLLO INDIA SERVICES (Mumbai)",
  "CMP-TST-01": "Testing Cafe (Mohali)",
  "CFSO5": "SAP11BLR (Bengaluru)",
  "AGFW26005": "BNY (Trial) (Pune)",
  "AGFW26014": "Boeing India WH1 (Kempapura)",
};

export function getDeviceDisplayName(serial: string): string {
  return DEVICE_DISPLAY_NAMES[serial] ?? serial;
}


function buildParams(filters: DashboardFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);
  if (filters.weeks.length) params.set("weeks", filters.weeks.join(","));
  if (filters.devices.length) params.set("devices", filters.devices.join(","));
  if (filters.mealTypes.length) params.set("meal_types", filters.mealTypes.join(","));
  if (filters.categories.length) params.set("categories", filters.categories.join(","));
  if (filters.wasteTypes.length) params.set("waste_types", filters.wasteTypes.join(","));
  return params;
}


async function fetchJson<T>(path: string, filters?: DashboardFilters): Promise<T> {
  const params = filters ? buildParams(filters).toString() : "";
  const search = params ? `${path.includes("?") ? "&" : "?"}${params}` : "";
  const response = await fetch(`/api/${path}${search}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.errors?.join?.(" ") || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}


export const dashboardApi = {
  getSummary: (filters: DashboardFilters) => fetchJson<DashboardSummary>("dashboard-summary", filters),
  getFoodItems: (filters: DashboardFilters) => fetchJson<NamedValue[]>("waste-by-food-item", filters),
  getWasteCategories: (filters: DashboardFilters) => fetchJson<NamedValue[]>("waste-by-category", filters),
  getMeals: (filters: DashboardFilters) => fetchJson<NamedValue[]>("waste-by-meal", filters),
  getTrend: (filters: DashboardFilters) => fetchJson<TrendPoint[]>("daily-waste-trend", filters),
  getAnomalies: (filters: DashboardFilters) => fetchJson<Array<{ date: string; value: number }>>("anomaly-days", filters),
  getWeeklyWaste: (filters: DashboardFilters) => fetchJson<WeekPoint[]>("weekly-waste", filters),
  getWeekdayWaste: (filters: DashboardFilters) => fetchJson<WeekdayPoint[]>("waste-by-weekday", filters),
  getTopDevices: (filters: DashboardFilters) => fetchJson<NamedValue[]>("top-devices", filters),
  getInsights: (filters: DashboardFilters) => fetchJson<DashboardInsights>("dashboard-insights", filters),
  getFilterOptions: () => fetchJson<FilterOptions>("filter-options"),
  getUsageAnalytics: (filters: DashboardFilters) => fetchJson<UsageAnalytics>("usage-analytics", filters),
  getBainMarieAnalytics: (filters: DashboardFilters) => fetchJson<BainMarieAnalytics>("bain-marie-analytics", filters),
  getDailyAvgByCategory: (filters: DashboardFilters) => fetchJson<NamedValue[]>("daily-avg-by-category", filters),
  getMealBreakdown: async (filters: DashboardFilters, wasteTypes: string[]) => {
    const params = buildParams(filters);
    if (wasteTypes.length) params.set("waste_types", wasteTypes.join(","));
    const response = await fetch(`/api/waste-by-meal?${params.toString()}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.errors?.join?.(" ") || `Request failed: ${response.status}`);
    }
    return response.json() as Promise<NamedValue[]>;
  },
  getWeekdayComparisonGrid: async (filters: DashboardFilters, weeks: string[], wasteTypes: string[]) => {
    const params = buildParams(filters);
    if (weeks.length) params.set("weeks", weeks.join(","));
    if (wasteTypes.length) params.set("waste_types", wasteTypes.join(","));
    const response = await fetch(`/api/weekday-comparison-grid?${params.toString()}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.errors?.join?.(" ") || `Request failed: ${response.status}`);
    }
    return response.json() as Promise<WeekdayComparisonGrid>;
  },
  askChat: async (question: string, provider: "local" | "gemini", filters: DashboardFilters) => {
    const chatFilters = {
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      weeks: filters.weeks.join(","),
      devices: filters.devices.join(","),
      meal_types: filters.mealTypes.join(","),
      categories: filters.categories.join(","),
    };
    const response = await fetch("/api/chat-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, provider, filters: chatFilters }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.errors?.join?.(" ") || `Request failed: ${response.status}`);
    }
    return response.json() as Promise<{ provider: string; answer: string }>;
  },
};

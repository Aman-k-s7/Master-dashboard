import { useEffect, useMemo, useState } from "react";
import { Printer } from "lucide-react";

import AlertsAnomalies from "@/components/dashboard/AlertsAnomalies";
import BainMarieAnalytics from "@/components/dashboard/BainMarieAnalytics";
import ChatBar from "@/components/dashboard/ChatBar";
import CoreAnalysis from "@/components/dashboard/CoreAnalysis";
import CostImpact from "@/components/dashboard/CostImpact";
import DailyAvgByCategory from "@/components/dashboard/DailyAvgByCategory";
import FilterSidebar from "@/components/dashboard/FilterSidebar";
import FinalInsights from "@/components/dashboard/FinalInsights";
import KpiStrip from "@/components/dashboard/KpiStrip";
import PatternDetection from "@/components/dashboard/PatternDetection";
import TimeAnalysis from "@/components/dashboard/TimeAnalysis";
import TrendAnalysis from "@/components/dashboard/TrendAnalysis";
import UsageAnalytics from "@/components/dashboard/UsageAnalytics";
import { useDashboardData, useDashboardFilterOptions } from "@/hooks/use-dashboard-data";
import type { DashboardFilters } from "@/lib/dashboard";


export default function Index() {
  const { data: filterOptions } = useDashboardFilterOptions();
  const [appliedFilters, setAppliedFilters] = useState<DashboardFilters>({
    devices: [],
    mealTypes: [],
    categories: [],
    wasteTypes: [],
    weeks: [],
  });

  useEffect(() => {
    if (!filterOptions) return;
    setAppliedFilters({
      dateFrom: filterOptions.min_date ?? undefined,
      dateTo: filterOptions.max_date ?? undefined,
      devices: filterOptions.devices,
      mealTypes: filterOptions.meal_types,
      categories: filterOptions.categories,
      wasteTypes: filterOptions.waste_types ?? [],
      weeks: [],
    });
  }, [filterOptions]);

  const filters = useMemo(() => appliedFilters, [appliedFilters]);
  const dashboard = useDashboardData(filters);

  return (
    <div className="flex min-h-screen bg-background">
      <div className="print-hide">
        <FilterSidebar options={filterOptions} onApply={setAppliedFilters} />
      </div>

      <main className="flex-1 overflow-y-auto">
        <div className="px-8 pt-6 pb-4 border-b border-border bg-card print-hide">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-foreground">Waste Analysis</h1>
              <p className="text-sm text-muted-foreground mt-0.5">Real-time food waste intelligence dashboard</p>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => window.print()}
                className="flex items-center gap-1.5 rounded border border-border bg-card px-3 py-1.5 text-sm text-foreground hover:bg-muted/50 transition-colors"
              >
                <Printer className="h-4 w-4" />
                Download PDF
              </button>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse" />
                Waste Analysis
              </div>
            </div>
          </div>
        </div>

        <div className="px-8 py-6 space-y-6">
          <div className="print-hide">
            <ChatBar filters={filters} />
          </div>

          {dashboard.isError ? (
            <div className="rounded border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              {dashboard.error?.message ?? "Dashboard data could not be loaded."}
            </div>
          ) : null}

          <KpiStrip summary={dashboard.summary} />

          <CoreAnalysis
            filters={filters}
            foodItems={dashboard.foodItems}
            wasteCategories={dashboard.wasteCategories}
            topDevices={dashboard.topDevices}
          />

          <TrendAnalysis trend={dashboard.trend} />

          <TimeAnalysis filters={filters} options={filterOptions} weeklyWaste={dashboard.weeklyWaste} />

          <AlertsAnomalies foodItems={dashboard.foodItems} wasteCategories={dashboard.wasteCategories} anomalies={dashboard.anomalies} />

          <PatternDetection insights={dashboard.insights} />

          <UsageAnalytics data={dashboard.usageAnalytics} />

          <BainMarieAnalytics data={dashboard.bainMarieAnalytics} />

          <DailyAvgByCategory data={dashboard.dailyAvgByCategory} />

          <CostImpact summary={dashboard.summary} />

          <FinalInsights insights={dashboard.insights} />
        </div>
      </main>
    </div>
  );
}

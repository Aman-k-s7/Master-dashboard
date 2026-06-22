import { AlertTriangle, Cpu, Leaf, Scale, ScanLine, Wind } from "lucide-react";

import type { DashboardSummary } from "@/lib/dashboard";


interface KpiStripProps {
  summary?: DashboardSummary;
}


export default function KpiStrip({ summary }: KpiStripProps) {
  const kpis = [
    { label: "Total Waste", value: `${(summary?.total_waste ?? 0).toLocaleString()} kg`, icon: Scale, color: "text-primary" },
    { label: "Total Scans", value: (summary?.total_scans ?? 0).toLocaleString(), icon: ScanLine, color: "text-primary" },
    { label: "Average Daily Waste", value: `${(summary?.average_daily_waste ?? 0).toLocaleString()} kg`, icon: Leaf, color: "text-primary" },
    { label: "Total Devices", value: (summary?.total_devices ?? 0).toString(), icon: Cpu, color: "text-primary" },
    { label: "Abnormal Days", value: (summary?.abnormal_days ?? 0).toString(), icon: AlertTriangle, color: "text-destructive" },
    { label: "Total CO\u2082e (kg)*", value: `${(summary?.co2_impact ?? 0).toLocaleString()} kg`, icon: Wind, color: "text-accent" },
  ];

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-6 gap-3">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="kpi-card flex items-center gap-3">
            <div className={`${kpi.color} shrink-0`}>
              <kpi.icon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground truncate">{kpi.label}</p>
              <p className="text-lg font-bold leading-tight text-foreground">{kpi.value}</p>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed px-1">
        *CO&#x2082;e figures based on avg emission factors (1.75&nbsp;kg CO&#x2082;e/kg food waste). Emission factors are applied based on procurement weight basis. Cooked weight is used as a conservative proxy. Cooking energy not included; values are indicative.
      </p>
    </div>
  );
}

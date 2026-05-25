import { Clock3, Wind, Utensils, Weight } from "lucide-react";

import type { DashboardSummary } from "@/lib/dashboard";


interface CostImpactProps {
  summary?: DashboardSummary;
}


export default function CostImpact({ summary }: CostImpactProps) {
  const items = [
    { label: "Total CO\u2082e (kg)", value: `${(summary?.co2_impact ?? 0).toLocaleString()} kgs`, icon: Wind, color: "text-primary" },
    { label: "Most Wasted Food", value: summary?.most_wasted_food?.name ?? "-", icon: Utensils, color: "text-accent" },
    { label: "Peak Waste Meal", value: summary?.peak_waste_meal?.name ?? "-", icon: Clock3, color: "text-primary" },
    { label: "Top Food Weight", value: `${(summary?.most_wasted_food?.value ?? 0).toLocaleString()} kg`, icon: Weight, color: "text-destructive" },
  ];

  return (
    <div className="grid grid-cols-4 gap-3">
      {items.map((item) => (
        <div key={item.label} className="kpi-card flex items-center gap-3">
          <div className={`${item.color} shrink-0`}>
            <item.icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="text-lg font-bold text-foreground">{item.value}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

import { Activity, Calendar, Cpu, ScanLine } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { UsageAnalytics as UsageAnalyticsType } from "@/lib/dashboard";


const COLORS = [
  "hsl(155,43%,21%)",
  "hsl(38,92%,50%)",
  "hsl(200,70%,50%)",
  "hsl(270,60%,55%)",
  "hsl(0,84%,60%)",
  "hsl(160,60%,40%)",
];


interface UsageAnalyticsProps {
  data?: UsageAnalyticsType;
}


export default function UsageAnalytics({ data }: UsageAnalyticsProps) {
  const kpis = [
    { label: "Total Scans", value: (data?.total_scans ?? 0).toLocaleString(), icon: ScanLine, color: "text-primary" },
    { label: "Active Days", value: (data?.active_days ?? 0).toString(), icon: Calendar, color: "text-primary" },
    { label: "Scans / Day", value: (data?.scans_per_day ?? 0).toString(), icon: Activity, color: "text-accent" },
    { label: "Devices", value: (data?.total_devices ?? 0).toString(), icon: Cpu, color: "text-primary" },
  ];

  return (
    <div className="chart-card space-y-4">
      <h3 className="section-title">Usage Analytics</h3>

      <div className="grid grid-cols-4 gap-3">
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

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm font-medium text-foreground mb-2">Scans by Meal</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data?.scans_by_meal ?? []} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 4 }} />
              <Bar dataKey="value" name="Scans" radius={[3, 3, 0, 0]}>
                {(data?.scans_by_meal ?? []).map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div>
          <p className="text-sm font-medium text-foreground mb-2">Scans by Waste Type</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data?.scans_by_waste_type ?? []} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 120 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={115} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 4 }} />
              <Bar dataKey="value" name="Scans" fill="hsl(155,43%,21%)" radius={[0, 3, 3, 0]}>
                {(data?.scans_by_waste_type ?? []).map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

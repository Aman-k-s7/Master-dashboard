import { Activity, Calendar, Scale } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { BainMarieAnalytics as BainMarieAnalyticsType } from "@/lib/dashboard";


const COLORS = [
  "hsl(155,43%,21%)",
  "hsl(38,92%,50%)",
  "hsl(200,70%,50%)",
  "hsl(270,60%,55%)",
  "hsl(0,84%,60%)",
  "hsl(160,60%,40%)",
];


interface BainMarieAnalyticsProps {
  data?: BainMarieAnalyticsType;
}


export default function BainMarieAnalytics({ data }: BainMarieAnalyticsProps) {
  const kpis = [
    { label: "Total Bain Marie Waste", value: `${(data?.kpi.total_waste ?? 0).toLocaleString()} kg`, icon: Scale, color: "text-primary" },
    { label: "Daily Average", value: `${(data?.kpi.daily_average ?? 0).toLocaleString()} kg`, icon: Activity, color: "text-accent" },
    { label: "Active Days", value: (data?.kpi.active_days ?? 0).toString(), icon: Calendar, color: "text-primary" },
  ];

  const topFood = (data?.top_food_items ?? []).slice(0, 8);

  return (
    <div className="chart-card space-y-4">
      <h3 className="section-title">Bain Marie Analytics</h3>

      <div className="grid grid-cols-3 gap-3">
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
          <p className="text-sm font-medium text-foreground mb-2">Top Food Items</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={topFood} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 110 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
              <XAxis type="number" tick={{ fontSize: 11 }} unit=" kg" />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={105} />
              <Tooltip
                formatter={(v: number) => [`${v.toLocaleString()} kg`, "Waste"]}
                contentStyle={{ fontSize: 12, borderRadius: 4 }}
              />
              <Bar dataKey="value" fill="hsl(155,43%,21%)" radius={[0, 3, 3, 0]}>
                {topFood.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div>
          <p className="text-sm font-medium text-foreground mb-2">By Meal</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data?.by_meal ?? []} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11 }} unit=" kg" />
              <Tooltip
                formatter={(v: number) => [`${v.toLocaleString()} kg`, "Waste"]}
                contentStyle={{ fontSize: 12, borderRadius: 4 }}
              />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {(data?.by_meal ?? []).map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-foreground mb-2">Daily Trend</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data?.daily_trend ?? []} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11 }} unit=" kg" />
            <Tooltip
              formatter={(v: number) => [`${v.toLocaleString()} kg`, "Bain Marie Waste"]}
              contentStyle={{ fontSize: 12, borderRadius: 4 }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="hsl(155,43%,21%)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

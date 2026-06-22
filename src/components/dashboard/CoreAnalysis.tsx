import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import MealTypeBreakdown from "@/components/dashboard/MealTypeBreakdown";
import type { DashboardFilters, NamedValue } from "@/lib/dashboard";
import { getDeviceDisplayName } from "@/lib/dashboard";


const COLORS = ["hsl(155,43%,21%)", "hsl(38,92%,50%)", "hsl(200,70%,50%)", "hsl(270,60%,55%)", "hsl(0,84%,60%)", "hsl(160,60%,40%)", "hsl(30,80%,55%)"];


interface CoreAnalysisProps {
  filters: DashboardFilters;
  foodItems: NamedValue[];
  wasteCategories: NamedValue[];
  topDevices: NamedValue[];
}


export default function CoreAnalysis({ filters, foodItems, wasteCategories, topDevices }: CoreAnalysisProps) {
  const topFoodItems = foodItems.slice(0, 7);
  const namedDevices = topDevices.map((d) => ({ ...d, name: getDeviceDisplayName(d.name) }));

  return (
    <div className="space-y-4">
      <div className="chart-card">
        <h3 className="section-title">Most Wasted Food</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={topFoodItems} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} angle={-15} textAnchor="end" height={60} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 4 }} />
            <Bar dataKey="value" radius={[3, 3, 0, 0]}>
              {topFoodItems.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <MealTypeBreakdown filters={filters} />

        <div className="chart-card">
          <h3 className="section-title">Waste Produced per Site</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={namedDevices} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 160 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={155} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 4 }} />
              <Bar dataKey="value" fill="hsl(155,43%,21%)" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

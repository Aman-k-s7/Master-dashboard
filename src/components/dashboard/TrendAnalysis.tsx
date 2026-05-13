import { format, parseISO } from "date-fns";
import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { TrendPoint } from "@/lib/dashboard";


interface TrendAnalysisProps {
  trend: TrendPoint[];
}


export default function TrendAnalysis({ trend }: TrendAnalysisProps) {
  const chartData = trend.map((point) => ({
    ...point,
    label: format(parseISO(point.date), "MMM d"),
  }));
  const spikes = chartData.filter((point) => point.spike);

  // Auto-adjust interval based on data length to prevent label overlap
  const getInterval = () => {
    const dataLength = chartData.length;
    if (dataLength <= 30) return 0; // Show all for <= 30 days
    if (dataLength <= 90) return Math.floor(dataLength / 15); // ~15 labels
    if (dataLength <= 180) return Math.floor(dataLength / 12); // ~12 labels
    return Math.floor(dataLength / 10); // ~10 labels for larger datasets
  };

  return (
    <div className="chart-card">
      <h3 className="section-title">Daily Waste Trend</h3>
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,13%,90%)" />
          <XAxis 
            dataKey="label" 
            tick={{ fontSize: 11 }} 
            interval={getInterval()} 
            angle={-45} 
            textAnchor="end" 
            height={70}
            minTickGap={5}
          />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 4 }} />
          <Line type="monotone" dataKey="value" stroke="hsl(155,43%,21%)" strokeWidth={2} dot={false} />
          {spikes.map((point) => (
            <ReferenceDot key={point.date} x={point.label} y={point.value} r={5} fill="hsl(0,84%,60%)" stroke="none" />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-full bg-primary" /> Normal</span>
        <span className="flex items-center gap-1"><span className="inline-block w-2.5 h-2.5 rounded-full bg-destructive" /> Spike / Anomaly</span>
      </div>
    </div>
  );
}

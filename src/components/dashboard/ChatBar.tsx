import type { DashboardFilters } from "@/lib/dashboard";

const PRESET_QUESTIONS = [
  "What is the total waste recorded?",
  "How many waste scans have been recorded?",
  "What is the average daily waste?",
  "Which food item is wasted the most?",
  "Which meal time generates the highest waste?",
  "What is the breakdown of waste by category?",
  "How has waste trended over time?",
  "Which days had unusually high waste?",
  "What is the total waste for this week?",
  "Which device generated the most waste?",
];

interface ChatBarProps {
  filters: DashboardFilters;
}

export default function ChatBar(_props: ChatBarProps) {
  return (
    <div className="chart-card">
      <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wide">
        Suggested Questions
      </p>
      <ol className="space-y-1.5">
        {PRESET_QUESTIONS.map((item, index) => (
          <li key={item} className="flex items-start gap-2 text-sm text-foreground">
            <span className="shrink-0 text-xs text-muted-foreground w-5 pt-0.5">
              {index + 1}.
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

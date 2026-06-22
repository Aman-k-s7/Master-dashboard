import { useState } from "react";
import { Loader2, Send } from "lucide-react";

import { dashboardApi, type DashboardFilters } from "@/lib/dashboard";

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

export default function ChatBar({ filters }: ChatBarProps) {
  const [question, setQuestion] = useState(PRESET_QUESTIONS[0]);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submitQuestion(selectedQuestion?: string) {
    const finalQuestion = (selectedQuestion ?? question).trim();
    if (!finalQuestion) return;
    setQuestion(finalQuestion);
    setLoading(true);
    setError("");
    setAnswer("");
    try {
      const response = await dashboardApi.askChat(finalQuestion, "gemini", filters);
      setAnswer(response.answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chart-card space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2 bg-background border border-border rounded px-3 py-2">
          <span className="text-sm">🤖</span>
          <select
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="flex-1 bg-transparent text-sm text-foreground outline-none cursor-pointer"
          >
            {PRESET_QUESTIONS.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => void submitQuestion()}
          disabled={loading}
          className="h-9 w-9 flex items-center justify-center rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shrink-0 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {PRESET_QUESTIONS.map((item, index) => (
          <button
            key={item}
            onClick={() => void submitQuestion(item)}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              item === question
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-background text-muted-foreground hover:bg-muted/50"
            }`}
          >
            {index + 1}. {item}
          </button>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {answer ? (
        <div className="rounded border border-border bg-background px-4 py-3 text-sm text-foreground leading-relaxed whitespace-pre-wrap">
          {answer}
        </div>
      ) : null}
    </div>
  );
}

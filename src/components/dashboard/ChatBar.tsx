import * as React from "react";
import { Loader2, Send, Sparkles } from "lucide-react";

import { dashboardApi, type DashboardFilters } from "@/lib/dashboard";


const PRESET_QUESTIONS = [
  "What is the total waste recorded?",
  "Which food item is wasted the most?",
  "Which meal time generates the highest waste?",
  "What is the breakdown of waste by category?",
  "Which days had unusually high waste?",
  "Which device generated the most waste?",
  "How has waste trended over time?",
  "What is the average daily waste?",
  "Show me this week's total waste.",
  "What percentage of waste is plate waste?",
];


interface ChatBarProps {
  filters: DashboardFilters;
}


export default function ChatBar({ filters }: ChatBarProps) {
  const [question, setQuestion] = React.useState("");
  const [answer, setAnswer] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const inputRef = React.useRef<HTMLInputElement>(null);

  async function submitQuestion(text?: string) {
    const finalQuestion = (text ?? question).trim();
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

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !loading) void submitQuestion();
  }

  function selectPreset(q: string) {
    setQuestion(q);
    setAnswer("");
    inputRef.current?.focus();
  }

  return (
    <div className="chart-card space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <Sparkles className="h-4 w-4 text-primary" />
        <span className="text-sm font-semibold text-foreground">Ask the Dashboard</span>
      </div>

      {/* Free-text input */}
      <div className="flex items-center gap-2">
        <div className="flex-1 flex items-center gap-2 bg-background border border-border rounded px-3 py-2 focus-within:border-primary transition-colors">
          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your waste data…"
            className="flex-1 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
            disabled={loading}
          />
          {question && !loading && (
            <button
              onClick={() => { setQuestion(""); setAnswer(""); }}
              className="text-muted-foreground hover:text-foreground text-xs px-1"
            >
              ✕
            </button>
          )}
        </div>
        <button
          onClick={() => void submitQuestion()}
          className="h-9 w-9 flex items-center justify-center rounded bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shrink-0 disabled:opacity-50"
          disabled={loading || !question.trim()}
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>

      {/* Preset suggestion chips */}
      <div className="flex flex-wrap gap-2">
        {PRESET_QUESTIONS.map((item) => (
          <button
            key={item}
            onClick={() => selectPreset(item)}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              item === question
                ? "border-primary bg-primary/10 text-primary"
                : "border-border bg-background text-muted-foreground hover:bg-muted/50 hover:text-foreground"
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {/* Answer panel */}
      {answer ? (
        <div className="rounded border border-border bg-background px-4 py-3 text-sm text-foreground leading-relaxed whitespace-pre-wrap">
          {answer}
        </div>
      ) : null}
    </div>
  );
}


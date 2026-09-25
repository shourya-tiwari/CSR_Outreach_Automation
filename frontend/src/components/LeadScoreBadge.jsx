import { useState } from "react";
import { explainScore } from "../api/client";
import { PRIORITY_STYLES } from "../constants";

export default function LeadScoreBadge({ companyId, leadScore }) {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notConfigured, setNotConfigured] = useState(false);

  if (!leadScore) return null;

  const style = PRIORITY_STYLES[leadScore.priority] ?? "bg-slate-100 text-slate-600";

  const handleExplain = async () => {
    if (explanation !== null) {
      setExplanation(null);
      return;
    }
    setLoading(true);
    setNotConfigured(false);
    try {
      const result = await explainScore(companyId);
      if (!result.configured) {
        setNotConfigured(true);
      } else {
        setExplanation(result.explanation || "No explanation available.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
          Lead score: {leadScore.score}/100 · {leadScore.priority} Priority
        </span>
        <button
          type="button"
          onClick={handleExplain}
          disabled={loading}
          className="text-xs font-medium text-emerald-700 hover:underline disabled:opacity-60"
        >
          {loading ? "Loading…" : explanation !== null ? "Hide" : "Why?"}
        </button>
      </div>
      {notConfigured && (
        <p className="mt-1 text-xs text-slate-400">
          Score explanations need GEMINI_API_KEY set on the backend.
        </p>
      )}
      {explanation && (
        <p className="mt-1 max-w-md whitespace-pre-wrap text-xs text-slate-600">{explanation}</p>
      )}
    </div>
  );
}

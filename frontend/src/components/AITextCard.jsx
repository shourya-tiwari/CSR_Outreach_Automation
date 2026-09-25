import { useState } from "react";

export default function AITextCard({ title, buttonLabel, fetcher, companyId }) {
  const [text, setText] = useState(null);
  const [loading, setLoading] = useState(false);
  const [notConfigured, setNotConfigured] = useState(false);
  const [error, setError] = useState(null);

  const generate = async () => {
    setLoading(true);
    setError(null);
    setNotConfigured(false);
    try {
      const result = await fetcher(companyId);
      if (!result.configured) {
        setNotConfigured(true);
        setText(null);
      } else {
        setText(result.text || "No content generated.");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-800">{title}</h3>
        <button
          type="button"
          onClick={generate}
          disabled={loading}
          className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {loading ? "Generating…" : text ? "Regenerate" : buttonLabel}
        </button>
      </div>
      {error && <p className="text-xs text-rose-600">{error}</p>}
      {notConfigured && (
        <p className="text-xs text-slate-400">
          This needs GEMINI_API_KEY set on the backend to enable AI generation.
        </p>
      )}
      {text && <p className="whitespace-pre-wrap text-sm text-slate-700">{text}</p>}
      {!text && !loading && !notConfigured && !error && (
        <p className="text-xs text-slate-400">Not generated yet.</p>
      )}
    </div>
  );
}

import { timeAgo } from "../utils/time";

export default function ActivityTimeline({ activity }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">Activity Timeline</h2>

      {activity.length === 0 && <p className="text-sm text-slate-400">No activity yet.</p>}

      <ol className="space-y-3 border-l border-slate-200 pl-4">
        {activity.map((entry) => (
          <li key={entry.id} className="relative">
            <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-emerald-500" />
            <p className="text-sm text-slate-700">{entry.description}</p>
            <span className="text-xs text-slate-400">{timeAgo(entry.created_at)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

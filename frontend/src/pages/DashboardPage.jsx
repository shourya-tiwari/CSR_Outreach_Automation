import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboard } from "../api/client";
import StatusBadge from "../components/StatusBadge";

const KPI_TILES = [
  { key: "total_companies", label: "Total Companies" },
  { key: "contacted", label: "Companies Contacted" },
  { key: "replies_received", label: "Replies Received" },
  { key: "meetings_scheduled", label: "Meetings Scheduled" },
  { key: "proposals_sent", label: "Proposals Sent" },
  { key: "successful_partnerships", label: "Successful Partnerships" },
];

function FollowUpList({ items, emptyLabel, dateClass }) {
  if (items.length === 0) {
    return <p className="px-4 py-3 text-sm text-slate-400">{emptyLabel}</p>;
  }
  return (
    <ul className="divide-y divide-slate-100">
      {items.map((item) => (
        <li key={item.id} className="flex items-center justify-between px-4 py-2.5">
          <div>
            <Link
              to={`/companies/${item.id}`}
              className="text-sm font-medium text-emerald-700 hover:underline"
            >
              {item.name}
            </Link>
            <div className="mt-0.5">
              <StatusBadge status={item.status} />
            </div>
          </div>
          <span className={`text-xs font-medium ${dateClass}`}>{item.follow_up_date}</span>
        </li>
      ))}
    </ul>
  );
}

function timeAgo(isoString) {
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <p className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8 text-slate-400">Loading dashboard…</div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500">Outreach activity at a glance.</p>
      </header>

      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {KPI_TILES.map((tile) => (
          <div
            key={tile.key}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <div className="text-2xl font-semibold text-slate-900">{data.kpis[tile.key]}</div>
            <div className="mt-1 text-xs font-medium text-slate-500">{tile.label}</div>
          </div>
        ))}
      </div>

      <div className="mb-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-rose-700">
            Overdue ({data.follow_ups.overdue.length})
          </h2>
          <FollowUpList
            items={data.follow_ups.overdue}
            emptyLabel="No overdue follow-ups."
            dateClass="text-rose-600"
          />
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-amber-700">
            Due Today ({data.follow_ups.due_today.length})
          </h2>
          <FollowUpList
            items={data.follow_ups.due_today}
            emptyLabel="Nothing due today."
            dateClass="text-amber-600"
          />
        </div>
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-700">
            Upcoming ({data.follow_ups.upcoming.length})
          </h2>
          <FollowUpList
            items={data.follow_ups.upcoming}
            emptyLabel="Nothing upcoming."
            dateClass="text-slate-500"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <h2 className="border-b border-slate-100 px-4 py-3 text-sm font-semibold text-slate-700">
          Recent Activity
        </h2>
        {data.recent_activity.length === 0 ? (
          <p className="px-4 py-3 text-sm text-slate-400">No activity yet.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.recent_activity.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between px-4 py-2.5">
                <div className="text-sm text-slate-700">
                  <Link
                    to={`/companies/${entry.company_id}`}
                    className="font-medium text-emerald-700 hover:underline"
                  >
                    {entry.company_name}
                  </Link>
                  <span className="text-slate-500"> — {entry.description}</span>
                </div>
                <span className="whitespace-nowrap text-xs text-slate-400">
                  {timeAgo(entry.created_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

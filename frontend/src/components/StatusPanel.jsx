import { useState } from "react";
import { LEAD_STATUSES } from "../constants";
import { updateCompany } from "../api/client";

export default function StatusPanel({ company, onUpdated }) {
  const [saving, setSaving] = useState(false);

  const handleChange = async (field, value) => {
    setSaving(true);
    try {
      const updated = await updateCompany(company.id, { [field]: value || null });
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">Outreach status</h2>
      <div className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Status</label>
          <select
            value={company.status}
            disabled={saving}
            onChange={(e) => handleChange("status", e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            {LEAD_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Last contacted
          </label>
          <input
            type="date"
            value={company.last_contacted_date ?? ""}
            disabled={saving}
            onChange={(e) => handleChange("last_contacted_date", e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Follow-up date</label>
          <input
            type="date"
            value={company.follow_up_date ?? ""}
            disabled={saving}
            onChange={(e) => handleChange("follow_up_date", e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>
      </div>
    </div>
  );
}

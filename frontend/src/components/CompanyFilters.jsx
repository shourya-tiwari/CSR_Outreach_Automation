import { useState } from "react";
import { LEAD_STATUSES } from "../constants";

const FIELDS = [
  { key: "name", label: "Company name", type: "text" },
  { key: "industry", label: "Industry", type: "text" },
  { key: "city", label: "City", type: "text" },
  { key: "state", label: "State", type: "text" },
  { key: "csr_focus", label: "CSR focus", type: "text" },
];

const OPTIONAL_FIELDS = [
  { key: "min_revenue", label: "Min revenue (₹)", placeholder: "e.g. 10000000" },
  { key: "max_revenue", label: "Max revenue (₹)", placeholder: "e.g. 500000000" },
  { key: "min_employees", label: "Min employees", placeholder: "e.g. 50" },
  { key: "max_employees", label: "Max employees", placeholder: "e.g. 5000" },
];

export default function CompanyFilters({ filters, onChange, onReset }) {
  const [showOptional, setShowOptional] = useState(false);

  const handleField = (key) => (event) => {
    onChange({ ...filters, [key]: event.target.value });
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {FIELDS.map((field) => (
          <div key={field.key}>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              {field.label}
            </label>
            <input
              type="text"
              value={filters[field.key] ?? ""}
              onChange={handleField(field.key)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              placeholder={`Search by ${field.label.toLowerCase()}`}
            />
          </div>
        ))}

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Status</label>
          <select
            value={filters.status ?? ""}
            onChange={handleField("status")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">Any status</option>
            {LEAD_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Min CSR spending (₹)
          </label>
          <input
            type="number"
            value={filters.min_csr_spending ?? ""}
            onChange={handleField("min_csr_spending")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="e.g. 1000000"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Max CSR spending (₹)
          </label>
          <input
            type="number"
            value={filters.max_csr_spending ?? ""}
            onChange={handleField("max_csr_spending")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="e.g. 10000000"
          />
        </div>
      </div>

      <div className="mt-3">
        <button
          type="button"
          onClick={() => setShowOptional((v) => !v)}
          className="text-sm font-medium text-emerald-700 hover:text-emerald-800"
        >
          {showOptional ? "− Hide revenue / employee filters" : "+ More filters (revenue, employees)"}
        </button>
      </div>

      {showOptional && (
        <div className="mt-3 grid grid-cols-1 gap-3 border-t border-slate-100 pt-3 sm:grid-cols-2 lg:grid-cols-4">
          {OPTIONAL_FIELDS.map((field) => (
            <div key={field.key}>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                {field.label}
              </label>
              <input
                type="number"
                value={filters[field.key] ?? ""}
                onChange={handleField(field.key)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
                placeholder={field.placeholder}
              />
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={onReset}
          className="text-sm font-medium text-slate-500 hover:text-slate-700"
        >
          Clear filters
        </button>
      </div>
    </div>
  );
}

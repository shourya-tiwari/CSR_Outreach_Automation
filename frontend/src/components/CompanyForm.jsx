import { useState } from "react";
import Modal from "./Modal";

const EMPTY = {
  name: "",
  industry: "",
  city: "",
  state: "",
  website: "",
  csr_focus: "",
  csr_spending: "",
  revenue: "",
  employee_count: "",
};

const NUMERIC_FIELDS = new Set(["csr_spending", "revenue", "employee_count"]);

export default function CompanyForm({ onClose, onSubmit }) {
  const [values, setValues] = useState(EMPTY);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleChange = (key) => (event) => {
    setValues({ ...values, [key]: event.target.value });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!values.name.trim()) {
      setError("Company name is required.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload = { ...values };
      for (const field of NUMERIC_FIELDS) {
        payload[field] = payload[field] === "" ? null : Number(payload[field]);
      }
      for (const key of Object.keys(payload)) {
        if (payload[key] === "") payload[key] = null;
      }
      await onSubmit(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title="Add company" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            Company name *
          </label>
          <input
            autoFocus
            value={values.name}
            onChange={handleChange("name")}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Industry</label>
            <input
              value={values.industry}
              onChange={handleChange("industry")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">CSR focus</label>
            <input
              value={values.csr_focus}
              onChange={handleChange("csr_focus")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">City</label>
            <input
              value={values.city}
              onChange={handleChange("city")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">State</label>
            <input
              value={values.state}
              onChange={handleChange("state")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Website</label>
          <input
            value={values.website}
            onChange={handleChange("website")}
            placeholder="https://"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              CSR spending (₹)
            </label>
            <input
              type="number"
              value={values.csr_spending}
              onChange={handleChange("csr_spending")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Revenue (₹)</label>
            <input
              type="number"
              value={values.revenue}
              onChange={handleChange("revenue")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Employees</label>
            <input
              type="number"
              value={values.employee_count}
              onChange={handleChange("employee_count")}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save company"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

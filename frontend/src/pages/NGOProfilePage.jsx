import { useEffect, useState } from "react";
import { getNgoProfile, updateNgoProfile } from "../api/client";

const FIELDS = [
  { key: "name", label: "Organization name" },
  { key: "work_area", label: "Work area", placeholder: "e.g. educating underprivileged children" },
  { key: "focus_areas", label: "Focus areas (comma-separated)", placeholder: "e.g. Education, Healthcare" },
  { key: "city", label: "City" },
  { key: "state", label: "State" },
  { key: "contact_email", label: "Contact email" },
  { key: "contact_phone", label: "Contact phone" },
];

export default function NGOProfilePage() {
  const [profile, setProfile] = useState(null);
  const [values, setValues] = useState({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getNgoProfile()
      .then((data) => {
        setProfile(data);
        setValues(data);
      })
      .catch((err) => setError(err.message));
  }, []);

  const handleChange = (key) => (e) => {
    setValues({ ...values, [key]: e.target.value });
    setSaved(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await updateNgoProfile(values);
      setProfile(updated);
      setValues(updated);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (error && !profile) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-8">
        <p className="rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{error}</p>
      </div>
    );
  }

  if (!profile) {
    return <div className="mx-auto max-w-2xl px-4 py-8 text-slate-400">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">NGO Profile</h1>
        <p className="text-sm text-slate-500">
          Stored once, reused automatically in lead scoring and AI-generated emails.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        {FIELDS.map((field) => (
          <div key={field.key}>
            <label className="mb-1 block text-xs font-medium text-slate-600">{field.label}</label>
            <input
              value={values[field.key] ?? ""}
              onChange={handleChange(field.key)}
              placeholder={field.placeholder}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        ))}

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save profile"}
          </button>
          {saved && <span className="text-sm text-emerald-700">Saved.</span>}
        </div>
      </form>
    </div>
  );
}

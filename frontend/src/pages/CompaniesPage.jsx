import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listCompanies, createCompany } from "../api/client";
import CompanyFilters from "../components/CompanyFilters";
import CompanyForm from "../components/CompanyForm";
import StatusBadge from "../components/StatusBadge";
import { PRIORITY_STYLES } from "../constants";

const PAGE_SIZE = 25;

export default function CompaniesPage() {
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(0);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const updateFilters = (newFilters) => {
    setFilters(newFilters);
    setPage(0);
  };

  useEffect(() => {
    const timeout = setTimeout(() => {
      setLoading(true);
      listCompanies({ ...filters, skip: page * PAGE_SIZE, limit: PAGE_SIZE })
        .then(setCompanies)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }, 250); // debounce free-text filter typing

    return () => clearTimeout(timeout);
  }, [filters, page]);

  const handleCreate = async (payload, { force = false } = {}) => {
    await createCompany(payload, { force });
    setShowForm(false);
    listCompanies({ ...filters, skip: page * PAGE_SIZE, limit: PAGE_SIZE }).then(setCompanies);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Companies</h1>
          <p className="text-sm text-slate-500">
            Search for companies suitable for CSR outreach.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700"
        >
          + Add company
        </button>
      </header>

      <div className="mb-6">
        <CompanyFilters filters={filters} onChange={updateFilters} onReset={() => updateFilters({})} />
      </div>

      {error && (
        <p className="mb-4 rounded-lg bg-rose-50 px-4 py-2 text-sm text-rose-700">{error}</p>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Industry</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">CSR focus</th>
              <th className="px-4 py-3">Contacts</th>
              <th className="px-4 py-3">Lead Score</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && companies.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                  No companies match these filters yet.
                </td>
              </tr>
            )}
            {!loading &&
              companies.map((company) => (
                <tr key={company.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/companies/${company.id}`}
                      className="font-medium text-emerald-700 hover:underline"
                    >
                      {company.name}
                    </Link>
                    {company.website && (
                      <div className="text-xs text-slate-400">{company.website}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{company.industry || "—"}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {[company.city, company.state].filter(Boolean).join(", ") || "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{company.csr_focus || "—"}</td>
                  <td className="px-4 py-3 text-slate-600">{company.contact_count}</td>
                  <td className="px-4 py-3">
                    {company.lead_score ? (
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          PRIORITY_STYLES[company.lead_score.priority] ?? "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {company.lead_score.score}/100 · {company.lead_score.priority}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={company.status} />
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <span className="text-sm text-slate-500">
          {loading ? "Loading…" : `Showing ${companies.length ? page * PAGE_SIZE + 1 : 0}–${page * PAGE_SIZE + companies.length}`}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0 || loading}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            ← Previous
          </button>
          <button
            type="button"
            onClick={() => setPage((p) => p + 1)}
            disabled={companies.length < PAGE_SIZE || loading}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      </div>

      {showForm && (
        <CompanyForm onClose={() => setShowForm(false)} onSubmit={handleCreate} />
      )}
    </div>
  );
}

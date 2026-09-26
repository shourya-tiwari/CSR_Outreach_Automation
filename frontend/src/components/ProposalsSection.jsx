import { useState } from "react";
import { addProposal, deleteProposal, updateProposal } from "../api/client";
import { PROPOSAL_STAGES, PROPOSAL_STAGE_STYLES } from "../constants";

export default function ProposalsSection({ companyId, proposals, onChanged }) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      await addProposal(companyId, {
        title: title.trim(),
        amount: amount === "" ? null : Number(amount),
      });
      setTitle("");
      setAmount("");
      onChanged();
    } finally {
      setSaving(false);
    }
  };

  const handleStageChange = async (proposalId, stage) => {
    await updateProposal(proposalId, { stage });
    onChanged();
  };

  const handleDelete = async (proposalId) => {
    await deleteProposal(proposalId);
    onChanged();
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">Proposals ({proposals.length})</h2>

      <form onSubmit={handleAdd} className="mb-4 flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Proposal title…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="Amount (₹)"
          className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          Add
        </button>
      </form>

      {proposals.length === 0 && <p className="text-sm text-slate-400">No proposals yet.</p>}

      <ul className="space-y-2">
        {proposals.map((proposal) => (
          <li
            key={proposal.id}
            className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 p-2.5"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-slate-800">{proposal.title}</p>
              {proposal.amount != null && (
                <span className="text-xs text-slate-400">₹{proposal.amount.toLocaleString()}</span>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <select
                value={proposal.stage}
                onChange={(e) => handleStageChange(proposal.id, e.target.value)}
                className={`rounded-full border-0 px-2 py-1 text-xs font-medium ${
                  PROPOSAL_STAGE_STYLES[proposal.stage] ?? "bg-slate-100 text-slate-600"
                }`}
              >
                {PROPOSAL_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {stage}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => handleDelete(proposal.id)}
                className="text-xs text-rose-500 hover:underline"
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

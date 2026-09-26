import { useState } from "react";
import { addTagToCompany, removeTagFromCompany } from "../api/client";

export default function TagsSection({ companyId, tags, onChanged }) {
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    try {
      await addTagToCompany(companyId, name.trim());
      setName("");
      onChanged();
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (tagId) => {
    await removeTagFromCompany(companyId, tagId);
    onChanged();
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tags.map((tag) => (
        <span
          key={tag.id}
          className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700"
        >
          {tag.name}
          <button
            type="button"
            onClick={() => handleRemove(tag.id)}
            className="text-slate-400 hover:text-rose-600"
            aria-label={`Remove tag ${tag.name}`}
          >
            ✕
          </button>
        </span>
      ))}
      <form onSubmit={handleAdd} className="inline-flex items-center gap-1">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="+ Add tag"
          disabled={saving}
          className="w-24 rounded-full border border-dashed border-slate-300 px-2.5 py-0.5 text-xs focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
      </form>
    </div>
  );
}

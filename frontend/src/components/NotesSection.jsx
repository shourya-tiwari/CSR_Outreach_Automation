import { useState } from "react";
import { addNote, deleteNote } from "../api/client";

export default function NotesSection({ companyId, notes, onChanged }) {
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!body.trim()) return;
    setSaving(true);
    try {
      await addNote(companyId, body.trim());
      setBody("");
      onChanged();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (noteId) => {
    await deleteNote(noteId);
    onChanged();
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-900">Notes ({notes.length})</h2>

      <form onSubmit={handleAdd} className="mb-4 flex gap-2">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Add a note about a call, meeting, or discussion…"
          rows={2}
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
        <button
          type="submit"
          disabled={saving}
          className="self-start rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
        >
          Add
        </button>
      </form>

      {notes.length === 0 && <p className="text-sm text-slate-400">No notes yet.</p>}

      <ul className="space-y-3">
        {notes.map((note) => (
          <li key={note.id} className="rounded-lg bg-slate-50 p-3">
            <p className="text-sm text-slate-800 whitespace-pre-wrap">{note.body}</p>
            <div className="mt-1 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {new Date(note.created_at).toLocaleString()}
              </span>
              <button
                type="button"
                onClick={() => handleDelete(note.id)}
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

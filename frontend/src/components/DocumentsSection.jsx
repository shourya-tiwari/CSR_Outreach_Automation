import { useRef, useState } from "react";
import { deleteDocument, documentDownloadUrl, uploadDocument } from "../api/client";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsSection({ companyId, documents, onChanged }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(companyId, file);
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (documentId) => {
    await deleteDocument(documentId);
    onChanged();
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Documents ({documents.length})</h2>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-60"
        >
          {uploading ? "Uploading…" : "Upload"}
        </button>
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleUpload} />
      </div>

      {error && <p className="mb-2 text-xs text-rose-600">{error}</p>}
      {documents.length === 0 && (
        <p className="text-sm text-slate-400">
          No documents yet. Upload proposals, CSR reports, MoUs, or receipts.
        </p>
      )}

      <ul className="space-y-2">
        {documents.map((doc) => (
          <li key={doc.id} className="flex items-center justify-between rounded-lg bg-slate-50 p-2.5">
            <div className="min-w-0">
              <a
                href={documentDownloadUrl(doc.id)}
                className="block truncate text-sm font-medium text-emerald-700 hover:underline"
              >
                {doc.filename}
              </a>
              <span className="text-xs text-slate-400">
                {formatSize(doc.size)} · {new Date(doc.uploaded_at).toLocaleDateString()}
              </span>
            </div>
            <button
              type="button"
              onClick={() => handleDelete(doc.id)}
              className="ml-2 shrink-0 text-xs text-rose-500 hover:underline"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

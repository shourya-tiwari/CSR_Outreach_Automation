import { Routes, Route } from "react-router-dom";
import CompaniesPage from "./pages/CompaniesPage";
import CompanyDetailPage from "./pages/CompanyDetailPage";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
          <span className="text-lg">🤝</span>
          <span className="font-semibold text-slate-900">CSR Outreach Portal</span>
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<CompaniesPage />} />
        <Route path="/companies/:id" element={<CompanyDetailPage />} />
      </Routes>
    </div>
  );
}

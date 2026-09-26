import { NavLink, Routes, Route } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import CompaniesPage from "./pages/CompaniesPage";
import CompanyDetailPage from "./pages/CompanyDetailPage";
import NGOProfilePage from "./pages/NGOProfilePage";

const NAV_LINK_CLASS = ({ isActive }) =>
  `text-sm font-medium ${isActive ? "text-emerald-700" : "text-slate-500 hover:text-slate-700"}`;

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">🤝</span>
            <span className="font-semibold text-slate-900">CSR Outreach Portal</span>
          </div>
          <NavLink to="/" end className={NAV_LINK_CLASS}>
            Dashboard
          </NavLink>
          <NavLink to="/companies" className={NAV_LINK_CLASS}>
            Companies
          </NavLink>
          <NavLink to="/ngo-profile" className={NAV_LINK_CLASS}>
            NGO Profile
          </NavLink>
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/companies" element={<CompaniesPage />} />
        <Route path="/companies/:id" element={<CompanyDetailPage />} />
        <Route path="/ngo-profile" element={<NGOProfilePage />} />
      </Routes>
    </div>
  );
}

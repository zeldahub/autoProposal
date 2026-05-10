import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Generator from "./pages/Generator";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Projects from "./pages/Projects";
import ProjectsTrash from "./pages/ProjectsTrash";
import ProjectDetail from "./pages/ProjectDetail";
import Artifacts from "./pages/Artifacts";
import SettingsAi from "./pages/SettingsAi";
import Profile from "./pages/Profile";
import NotificationsPage from "./pages/Notifications";
import AdminLayout from "./components/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminAudit from "./pages/admin/AdminAudit";
import AdminCategories from "./pages/admin/AdminCategories";
import AdminJobs from "./pages/admin/AdminJobs";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AdminRoute } from "./auth/AdminRoute";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Dashboard />} />
        <Route path="/generator" element={<Generator />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/trash" element={<ProjectsTrash />} />
        <Route path="/projects/:uuid" element={<ProjectDetail />} />
        <Route path="/artifacts" element={<Artifacts />} />
        <Route path="/settings" element={<Navigate to="/settings/ai" replace />} />
        <Route path="/settings/ai" element={<SettingsAi />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/notifications" element={<NotificationsPage />} />

        <Route
          path="/admin"
          element={<AdminRoute><AdminLayout /></AdminRoute>}
        >
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="audit" element={<AdminAudit />} />
          <Route path="category" element={<AdminCategories />} />
          <Route path="jobs" element={<AdminJobs />} />
        </Route>

        <Route path="*" element={<Navigate to="/generator" replace />} />
      </Route>
    </Routes>
  );
}

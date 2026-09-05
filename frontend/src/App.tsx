import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/layouts/AppLayout";
import AuthLayout from "@/layouts/AuthLayout";
import Analytics from "@/pages/Analytics";
import ApplicationDetail from "@/pages/ApplicationDetail";
import Applications from "@/pages/Applications";
import Automation from "@/pages/Automation";
import ComingSoon from "@/pages/ComingSoon";
import Dashboard from "@/pages/Dashboard";
import JobDetail from "@/pages/JobDetail";
import Jobs from "@/pages/Jobs";
import Login from "@/pages/Login";
import Profile from "@/pages/Profile";
import RapidApply from "@/pages/RapidApply";
import Register from "@/pages/Register";
import ResumePage from "@/pages/Resume";
import Settings from "@/pages/Settings";
import VerifyEmail from "@/pages/VerifyEmail";

export default function App() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:id" element={<JobDetail />} />
          <Route path="/rapid-apply" element={<RapidApply />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/applications/:id" element={<ApplicationDetail />} />
          <Route path="/interviews" element={<ComingSoon title="Interviews" phase="Phase 6" />} />
          <Route path="/resume" element={<ResumePage />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/automation" element={<Automation />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

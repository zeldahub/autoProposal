import { Navigate, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./context";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, token } = useAuth();
  const loc = useLocation();
  if (!user || !token) {
    const redirect = encodeURIComponent(loc.pathname + loc.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }
  return <>{children}</>;
}

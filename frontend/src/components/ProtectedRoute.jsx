import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090E0A]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-[#557945] border-t-[#FFCB3D] rounded-full animate-spin" />
          <p className="text-[#A2B5A6] font-medium text-xs">Verifying authorization &amp; credentials...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Account status check
  if (user?.status && user.status !== 'active') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090E0A] p-4 font-sans">
        <div className="max-w-md w-full glass-panel-elevated rounded-3xl p-6 text-center shadow-2xl border border-rose-500/30">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[#F1F6F2] mb-2">Account {user.status}</h2>
          <p className="text-[#A2B5A6] text-xs mb-6">
            Your account status is currently marked as <span className="font-semibold text-rose-300">{user.status}</span>. Please contact platform administrators.
          </p>
          <button
            onClick={logout}
            className="w-full py-2.5 bg-[#142017] hover:bg-[#1C2F20] text-[#F1F6F2] border border-[#557945]/30 font-semibold rounded-xl text-xs transition"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  // Role check
  if (allowedRoles && allowedRoles.length > 0 && !allowedRoles.includes(user?.role)) {
    const defaultDashboard =
      user?.role === 'admin' ? '/admin' : user?.role === 'mentor' ? '/mentor' : '/student';

    return (
      <div className="min-h-screen flex items-center justify-center bg-[#090E0A] p-4 font-sans">
        <div className="max-w-md w-full glass-panel-elevated rounded-3xl p-6 text-center shadow-2xl border border-[#FFCB3D]/30">
          <ShieldAlert className="w-12 h-12 text-[#FFCB3D] mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[#F1F6F2] mb-2">Access Denied</h2>
          <p className="text-[#A2B5A6] text-xs mb-4">
            You do not have permission to access this page. This area requires one of the following roles:{' '}
            <span className="text-[#FFCB3D] font-bold">{allowedRoles.join(', ')}</span>.
          </p>
          <p className="text-xs text-[#8BA190] mb-6">
            Your active role: <span className="font-bold text-[#F1F6F2] uppercase">{user?.role}</span>
          </p>
          <div className="flex gap-3">
            <Link
              to={defaultDashboard}
              className="flex-1 py-2.5 bg-gradient-to-r from-[#FFCB3D] to-[#F1A344] text-[#090E0A] font-bold rounded-xl text-xs transition text-center hover:brightness-105"
            >
              Go to My Dashboard
            </Link>
            <button
              onClick={logout}
              className="px-4 py-2.5 bg-[#142017] hover:bg-[#1C2F20] text-[#D0DDD2] border border-[#557945]/30 font-medium rounded-xl text-xs transition"
            >
              Log Out
            </button>
          </div>
        </div>
      </div>
    );
  }

  return children;
}

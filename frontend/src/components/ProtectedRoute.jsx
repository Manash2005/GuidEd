import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, AlertTriangle } from 'lucide-react';

export default function ProtectedRoute({ allowedRoles, children }) {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-3 border-[#D0D5DD] border-t-[#315E9E] rounded-full animate-spin" />
          <p className="text-[#667085] font-medium text-sm">Verifying authorization...</p>
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
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] p-4 font-sans">
        <div className="max-w-md w-full bg-white rounded-xl p-6 text-center shadow-sm border border-[#E4E7EC]">
          <AlertTriangle className="w-12 h-12 text-[#D92D20] mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[#202124] mb-2">Account {user.status}</h2>
          <p className="text-[#667085] text-sm mb-6">
            Your account status is currently marked as <span className="font-semibold text-[#D92D20]">{user.status}</span>. Please contact platform administrators.
          </p>
          <button
            onClick={logout}
            className="w-full py-2.5 bg-[#F2F4F7] hover:bg-[#E4E7EC] text-[#202124] border border-[#D0D5DD] font-semibold rounded-lg text-sm transition"
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
      <div className="min-h-screen flex items-center justify-center bg-[#F8F9FA] p-4 font-sans">
        <div className="max-w-md w-full bg-white rounded-xl p-6 text-center shadow-sm border border-[#E4E7EC]">
          <ShieldAlert className="w-12 h-12 text-[#315E9E] mx-auto mb-4" />
          <h2 className="text-xl font-bold text-[#202124] mb-2">Access Denied</h2>
          <p className="text-[#667085] text-sm mb-4">
            You do not have permission to access this page. This area requires one of the following roles:{' '}
            <span className="text-[#315E9E] font-semibold">{allowedRoles.join(', ')}</span>.
          </p>
          <p className="text-xs text-[#667085] mb-6">
            Your active role: <span className="font-semibold text-[#202124] uppercase">{user?.role}</span>
          </p>
          <div className="flex gap-3">
            <Link
              to={defaultDashboard}
              className="flex-1 py-2.5 bg-[#315E9E] hover:bg-[#26497B] text-white font-semibold rounded-lg text-sm transition text-center"
            >
              Go to My Dashboard
            </Link>
            <button
              onClick={logout}
              className="px-4 py-2.5 bg-white hover:bg-[#F9FAFB] text-[#344054] border border-[#D0D5DD] font-medium rounded-lg text-sm transition"
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

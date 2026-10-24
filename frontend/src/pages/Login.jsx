import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getMentorPassword } from '../services/api';
import {
  Lock,
  Mail,
  ArrowRight,
  ShieldCheck,
  UserCheck,
  GraduationCap,
  Copy,
  Check
} from 'lucide-react';

export default function Login() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [copiedPwd, setCopiedPwd] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || null;

  const isMentorIdFormat = (id) => /^m\d{3}$/i.test(id.trim());

  const handleFillDerivedPassword = () => {
    if (isMentorIdFormat(identifier)) {
      setPassword(getMentorPassword(identifier));
    }
  };

  const handleCopyPassword = (pwd) => {
    navigator.clipboard.writeText(pwd);
    setCopiedPwd(true);
    setTimeout(() => setCopiedPwd(false), 2000);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const user = await login(identifier.trim(), password);
      if (from) {
        navigate(from, { replace: true });
      } else {
        if (user.role === 'admin') navigate('/admin', { replace: true });
        else if (user.role === 'mentor') navigate('/mentor', { replace: true });
        else navigate('/student', { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickLogin = async (ident, pwd) => {
    setIdentifier(ident);
    setPassword(pwd);
    setError('');
    setIsSubmitting(true);
    try {
      const user = await login(ident, pwd);
      if (user.role === 'admin') navigate('/admin', { replace: true });
      else if (user.role === 'mentor') navigate('/mentor', { replace: true });
      else navigate('/student', { replace: true });
    } catch (err) {
      setError(err.message || `Failed to log in as ${ident}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#202124] flex flex-col justify-center py-12 px-4 sm:px-6 font-sans">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#315E9E] text-white font-bold text-lg mb-3 shadow-xs">
          MC
        </div>
        <h1 className="text-2xl font-bold text-[#202124] tracking-tight">
          Mentor Connect
        </h1>
        <p className="text-sm text-[#667085] mt-1">
          Sign in to your career mentorship workspace
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 rounded-xl sm:px-8 shadow-sm border border-[#E4E7EC]">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-[#D92D20] text-xs font-medium">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">
                Email or Mentor ID
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-[#98A2B3]" />
                </div>
                <input
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="student@example.com or M001"
                  className="block w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:ring-2 focus:ring-[#315E9E]/15 transition"
                />
              </div>

              {isMentorIdFormat(identifier) && (
                <div className="mt-2 p-2 rounded-lg bg-[#EFF4FA] border border-[#D0DCEB] flex items-center justify-between text-xs">
                  <span className="text-[#315E9E]">
                    Password: <code className="font-mono font-bold">{getMentorPassword(identifier)}</code>
                  </span>
                  <button
                    type="button"
                    onClick={handleFillDerivedPassword}
                    className="text-xs font-semibold text-[#315E9E] hover:underline cursor-pointer"
                  >
                    Auto-Fill
                  </button>
                </div>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-[#344054]">Password</label>
                {isMentorIdFormat(identifier) && (
                  <button
                    type="button"
                    onClick={() => handleCopyPassword(getMentorPassword(identifier))}
                    className="text-xs text-[#667085] hover:text-[#315E9E] flex items-center gap-1 cursor-pointer"
                  >
                    {copiedPwd ? <Check className="w-3.5 h-3.5 text-[#12B76A]" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedPwd ? 'Copied' : 'Copy'}</span>
                  </button>
                )}
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-[#98A2B3]" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:ring-2 focus:ring-[#315E9E]/15 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex justify-center items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-[#315E9E] hover:bg-[#26497B] transition disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <span>{isSubmitting ? 'Signing in...' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4 text-white" />
            </button>
          </form>

          {/* Quick Access Shortcuts */}
          <div className="mt-5 pt-4 border-t border-[#E4E7EC] space-y-2.5">
            <span className="text-[11px] font-semibold text-[#667085] uppercase tracking-wider block">
              Quick Role Sign In
            </span>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin('student@example.com', 'StudentPass123!')}
                className="p-2.5 rounded-lg border border-[#E4E7EC] bg-[#F8F9FA] hover:bg-[#EFF4FA] hover:border-[#315E9E]/40 text-left transition cursor-pointer"
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[#202124] mb-0.5">
                  <GraduationCap className="w-3.5 h-3.5 text-[#315E9E]" />
                  <span>Student</span>
                </div>
                <span className="text-[11px] text-[#667085] block truncate">Aarav Mehta</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('M001', getMentorPassword('M001'))}
                className="p-2.5 rounded-lg border border-[#E4E7EC] bg-[#F8F9FA] hover:bg-[#EFF4FA] hover:border-[#315E9E]/40 text-left transition cursor-pointer"
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[#202124] mb-0.5">
                  <UserCheck className="w-3.5 h-3.5 text-[#12B76A]" />
                  <span>Mentor</span>
                </div>
                <span className="text-[11px] text-[#667085] block truncate">ID: M001</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('admin@guided.app', 'AdminSecret2026!')}
                className="p-2.5 rounded-lg border border-[#E4E7EC] bg-[#F8F9FA] hover:bg-[#EFF4FA] hover:border-[#315E9E]/40 text-left transition cursor-pointer"
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-[#202124] mb-0.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#315E9E]" />
                  <span>Admin</span>
                </div>
                <span className="text-[11px] text-[#667085] block truncate">Operations</span>
              </button>
            </div>
          </div>

          <div className="mt-5 text-center text-xs text-[#667085]">
            New student?{' '}
            <Link to="/register" className="font-semibold text-[#315E9E] hover:underline">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

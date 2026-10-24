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
  Sparkles,
  Key,
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
    <div className="min-h-screen bg-[#090E0A] text-[#F1F6F2] flex flex-col justify-center py-12 px-4 sm:px-6 relative overflow-hidden font-sans">
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#5D9253]/15 blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 -right-40 w-[500px] h-[500px] rounded-full bg-[#FFCB3D]/10 blur-[150px] pointer-events-none" />

      {/* Brand - text only */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10 mb-6">
        <h1 className="text-3xl font-extrabold text-[#F1F6F2] tracking-tight">
          Guid<span className="text-[#FFCB3D]">Ed</span>
        </h1>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="glass-panel-elevated py-8 px-6 rounded-3xl sm:px-8 shadow-2xl border border-[#557945]/30">
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">
                Email or Mentor ID
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-[#557945]" />
                </div>
                <input
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="M001 or you@domain.com"
                  className="block w-full pl-10 pr-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] focus:outline-none"
                />
              </div>

              {isMentorIdFormat(identifier) && (
                <div className="mt-2 p-2 rounded-lg bg-[#5D9253]/15 border border-[#5D9253]/30 flex items-center justify-between text-[11px]">
                  <div className="flex items-center gap-1.5 text-[#84CC78]">
                    <span>Password: <code className="font-mono font-bold text-[#FFCB3D]">{getMentorPassword(identifier)}</code></span>
                  </div>
                  <button
                    type="button"
                    onClick={handleFillDerivedPassword}
                    className="text-[10px] font-bold text-[#FFCB3D] hover:underline"
                  >
                    Auto-Fill
                  </button>
                </div>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-[#D0DDD2]">Password</label>
                {isMentorIdFormat(identifier) && (
                  <button
                    type="button"
                    onClick={() => handleCopyPassword(getMentorPassword(identifier))}
                    className="text-[10px] text-[#A2B5A6] hover:text-[#FFCB3D] flex items-center gap-1"
                  >
                    {copiedPwd ? <Check className="w-3 h-3 text-[#5D9253]" /> : <Copy className="w-3 h-3 text-[#8BA190]" />}
                    <span>{copiedPwd ? 'Copied' : 'Copy'}</span>
                  </button>
                )}
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-[#557945]" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-10 pr-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 flex justify-center items-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold text-[#090E0A] bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] hover:brightness-105 shadow-md shadow-[#FFCB3D]/15 transition disabled:opacity-50 cursor-pointer"
            >
              <span>{isSubmitting ? 'Signing in...' : 'Sign In'}</span>
              <ArrowRight className="w-4 h-4 text-[#090E0A]" />
            </button>
          </form>

          {/* Quick Mentor Access & Reviewer Shortcuts */}
          <div className="mt-5 pt-4 border-t border-[#557945]/20 space-y-3">
            <div>
              <span className="text-[10px] font-bold text-[#8BA190] uppercase tracking-wider block mb-1.5">
                Mentor Quick Jump
              </span>
              <div className="flex flex-wrap gap-1.5">
                {['M001', 'M002', 'M005', 'M014', 'M021'].map((mid) => (
                  <button
                    key={mid}
                    type="button"
                    onClick={() => handleQuickLogin(mid, getMentorPassword(mid))}
                    className="px-2.5 py-1 rounded-lg bg-[#142017] hover:bg-[#1C2F20] border border-[#557945]/30 text-[11px] font-mono font-bold text-[#84CC78] hover:text-[#FFCB3D] transition"
                  >
                    {mid}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                type="button"
                onClick={() => handleQuickLogin('admin@guided.app', 'AdminPass123!Secure')}
                className="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-[#142017] hover:bg-[#1C2F20] border border-[#FFCB3D]/30 text-center transition"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-[#FFCB3D]" />
                <span className="text-[11px] font-semibold text-[#D0DDD2]">Admin</span>
              </button>

              <button
                type="button"
                onClick={() => handleQuickLogin('student@example.com', 'StudentPass123!')}
                className="flex items-center justify-center gap-1.5 p-2 rounded-xl bg-[#142017] hover:bg-[#1C2F20] border border-[#F1A344]/30 text-center transition"
              >
                <GraduationCap className="w-3.5 h-3.5 text-[#F1A344]" />
                <span className="text-[11px] font-semibold text-[#D0DDD2]">Student</span>
              </button>
            </div>
          </div>

          <div className="mt-5 text-center">
            <span className="text-xs text-[#8BA190]">New account? </span>
            <Link to="/register" className="text-xs font-semibold text-[#FFCB3D] hover:underline">
              Register
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

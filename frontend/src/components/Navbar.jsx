import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  MessageSquare,
  Calendar,
  Shield,
  Users,
  FileText,
  LogOut,
  UserCheck,
  Menu,
  X
} from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!user) return null;

  const roleStyles = {
    admin: {
      badge: 'bg-[#FFCB3D]/15 text-[#FFCB3D] border-[#FFCB3D]/30',
      label: 'Admin'
    },
    mentor: {
      badge: 'bg-[#5D9253]/20 text-[#84CC78] border-[#5D9253]/40',
      label: user.mentorId ? `Mentor ${user.mentorId}` : 'Mentor'
    },
    student: {
      badge: 'bg-[#F1A344]/15 text-[#F1A344] border-[#F1A344]/30',
      label: 'Student'
    }
  };

  const getNavLinks = () => {
    if (user.role === 'admin') {
      return [
        { to: '/admin', label: 'KPIs', icon: Shield },
        { to: '/admin?tab=users', label: 'Users', icon: Users },
        { to: '/admin?tab=bookings', label: 'Bookings', icon: Calendar },
        { to: '/admin?tab=audit', label: 'Audit', icon: FileText }
      ];
    }
    if (user.role === 'mentor') {
      return [
        { to: '/mentor', label: 'Sessions', icon: Calendar },
        { to: '/mentor?tab=profile', label: 'Profile', icon: UserCheck }
      ];
    }
    // Student links - strictly AI Advisor, Bookings, Profile (NO mentors directory)
    return [
      { to: '/student', label: 'AI Advisor', icon: MessageSquare },
      { to: '/student?tab=bookings', label: 'My Bookings', icon: Calendar },
      { to: '/student?tab=profile', label: 'Profile', icon: UserCheck }
    ];
  };

  const links = getNavLinks();

  return (
    <header className="fixed top-4 inset-x-0 z-50 mx-auto max-w-6xl px-3 sm:px-6">
      <div className="glass-floating-nav rounded-2xl px-4 sm:px-6 py-2.5 flex items-center justify-between transition-all">
        {/* Brand - clean text only, no logo icon */}
        <div className="flex items-center gap-6 sm:gap-8">
          <Link to="/" className="flex items-center gap-1.5 group">
            <span className="font-extrabold text-[#F1F6F2] text-lg tracking-tight">
              Guid<span className="text-[#FFCB3D]">Ed</span>
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {links.map((link) => {
              const Icon = link.icon;
              const linkBasePath = link.to.split('?')[0];
              const linkQuery = link.to.includes('?') ? link.to.split('?')[1] : '';
              const currentQuery = location.search ? location.search.substring(1) : '';

              const isActive =
                location.pathname === linkBasePath &&
                (linkQuery ? currentQuery === linkQuery : !currentQuery);

              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
                      : 'text-[#D0DDD2] hover:text-[#FFCB3D] hover:bg-[#152318]/60'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#FFCB3D]' : 'text-[#8BA190]'}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Side Controls */}
        <div className="flex items-center gap-3">
          {/* User Profile Badge */}
          <div className="flex items-center gap-3 pl-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-[#557945] to-[#5D9253] flex items-center justify-center text-[11px] font-bold text-white shadow-inner">
                {(user.fullName || user.email || 'U').charAt(0).toUpperCase()}
              </div>
              <div className="hidden sm:flex flex-col text-left">
                <span className="text-xs font-semibold text-[#F1F6F2] leading-tight">
                  {user.fullName || user.email?.split('@')[0]}
                </span>
                <span className="text-[10px] text-[#8BA190] font-mono leading-none">
                  {user.mentorId || (user.role === 'admin' ? 'Administrator' : 'Student')}
                </span>
              </div>
            </div>

            <span
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                roleStyles[user.role]?.badge || 'bg-[#557945]/20 text-[#84CC78] border-[#557945]/30'
              }`}
            >
              {roleStyles[user.role]?.label || user.role}
            </span>

            <button
              onClick={logout}
              className="p-1.5 rounded-xl text-[#8BA190] hover:text-rose-400 hover:bg-rose-500/10 transition"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          {/* Mobile Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 rounded-xl text-[#D0DDD2] hover:text-white hover:bg-[#152318] transition"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-2 glass-panel-elevated rounded-2xl p-4 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-150">
          <nav className="flex flex-col gap-1.5">
            {links.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-[#D0DDD2] hover:text-[#FFCB3D] hover:bg-[#152318] transition"
                >
                  <Icon className="w-4 h-4 text-[#5D9253]" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      )}
    </header>
  );
}

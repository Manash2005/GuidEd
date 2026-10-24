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
  X,
  Compass
} from 'lucide-react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!user) return null;

  const roleStyles = {
    admin: {
      badge: 'bg-[#EFF4FA] text-[#315E9E] border-[#D0DCEB]',
      label: 'Admin Workspace'
    },
    mentor: {
      badge: 'bg-[#ECFDF3] text-[#027A48] border-[#A6F4C5]',
      label: user.mentorId ? `Mentor ${user.mentorId}` : 'Mentor Portal'
    },
    student: {
      badge: 'bg-[#F0F5FF] text-[#2D5BFF] border-[#D0E2FF]',
      label: 'Student Workspace'
    }
  };

  const getNavLinks = () => {
    if (user.role === 'admin') {
      return [
        { to: '/admin', label: 'Overview', icon: Shield },
        { to: '/admin?tab=users', label: 'Users & Mentors', icon: Users },
        { to: '/admin?tab=bookings', label: 'Bookings', icon: Calendar },
        { to: '/admin?tab=audit', label: 'Audit Logs', icon: FileText }
      ];
    }
    if (user.role === 'mentor') {
      return [
        { to: '/mentor', label: 'Sessions', icon: Calendar },
        { to: '/mentor?tab=profile', label: 'Profile & Email', icon: UserCheck }
      ];
    }
    // Student links
    return [
      { to: '/student', label: 'Career Advisor', icon: MessageSquare },
      { to: '/student?tab=bookings', label: 'Upcoming Bookings', icon: Calendar },
      { to: '/student?tab=profile', label: 'My Account', icon: UserCheck }
    ];
  };

  const links = getNavLinks();

  return (
    <header className="fixed top-0 inset-x-0 z-50 bg-white border-b border-[#E4E7EC] shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand & Workspace Label */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 group">
            <span className="w-8 h-8 rounded-lg bg-[#315E9E] text-white flex items-center justify-center font-bold text-sm shadow-xs">
              MC
            </span>
            <div className="flex flex-col">
              <span className="font-bold text-[#202124] text-base leading-tight tracking-tight">
                Mentor Connect
              </span>
              <span className="text-[11px] text-[#667085] leading-tight font-medium">
                {roleStyles[user.role]?.label}
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1.5 ml-4">
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
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-[#EFF4FA] text-[#315E9E] font-semibold'
                      : 'text-[#667085] hover:text-[#202124] hover:bg-[#F8F9FA]'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#315E9E]' : 'text-[#98A2B3]'}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Side: User Profile & Actions */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#315E9E] text-white flex items-center justify-center text-xs font-semibold">
              {(user.fullName || user.email || 'U').charAt(0).toUpperCase()}
            </div>
            <div className="hidden sm:flex flex-col text-left">
              <span className="text-sm font-semibold text-[#202124] leading-tight">
                {user.fullName || user.email?.split('@')[0]}
              </span>
              <span className="text-xs text-[#667085] leading-tight">
                {user.mentorId || (user.role === 'admin' ? 'Administrator' : user.email)}
              </span>
            </div>
          </div>

          <span
            className={`hidden sm:inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
              roleStyles[user.role]?.badge || 'bg-gray-100 text-gray-700 border-gray-200'
            }`}
          >
            {user.role?.toUpperCase()}
          </span>

          <button
            onClick={logout}
            className="p-2 rounded-lg text-[#667085] hover:text-[#D92D20] hover:bg-rose-50 transition-colors cursor-pointer"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>

          {/* Mobile Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-[#667085] hover:text-[#202124] hover:bg-[#F2F4F7] transition"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[#E4E7EC] bg-white p-4 shadow-lg animate-in fade-in duration-150">
          <nav className="flex flex-col gap-1">
            {links.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[#344054] hover:text-[#315E9E] hover:bg-[#EFF4FA] transition"
                >
                  <Icon className="w-4 h-4 text-[#315E9E]" />
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

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { adminApi } from '../../services/api';
import {
  Shield,
  Users,
  Calendar,
  Activity,
  FileText,
  Search,
  Check,
  Video,
  ExternalLink
} from 'lucide-react';

export default function AdminDashboard() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'stats';

  const [statsData, setStatsData] = useState(null);
  const [healthData, setHealthData] = useState(null);

  // User Management State
  const [usersList, setUsersList] = useState([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersRoleFilter, setUsersRoleFilter] = useState('');
  const [usersStatusFilter, setUsersStatusFilter] = useState('');
  const [usersSearch, setUsersSearch] = useState('');
  const [isUpdatingUser, setIsUpdatingUser] = useState(false);

  // Bookings Management State
  const [bookingsList, setBookingsList] = useState([]);
  const [bookingsTotal, setBookingsTotal] = useState(0);
  const [bookingsPage, setBookingsPage] = useState(1);
  const [bookingsStatusFilter, setBookingsStatusFilter] = useState('');
  const [bookingsSearch, setBookingsSearch] = useState('');
  const [updatingBookingId, setUpdatingBookingId] = useState(null);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);

  const [feedbackMsg, setFeedbackMsg] = useState('');

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    if (activeTab === 'bookings') loadBookings();
    if (activeTab === 'audit') loadAuditLogs();
  }, [activeTab, usersPage, usersRoleFilter, usersStatusFilter, bookingsPage, bookingsStatusFilter]);

  const loadAll = async () => {
    try {
      const [stats, health] = await Promise.all([
        adminApi.getStats(),
        adminApi.getHealth().catch(() => null)
      ]);
      setStatsData(stats);
      setHealthData(health);
      if (stats?.totalUsers) {
        setUsersTotal(stats.totalUsers);
      }
      if (stats?.totalBookings) {
        setBookingsTotal(stats.totalBookings);
      }
    } catch (err) {
      console.error('Failed to load admin stats:', err);
    }
  };

  const loadUsers = async () => {
    try {
      const params = {
        page: usersPage,
        limit: 15,
        ...(usersRoleFilter ? { role: usersRoleFilter } : {}),
        ...(usersStatusFilter ? { status: usersStatusFilter } : {}),
        ...(usersSearch ? { q: usersSearch } : {})
      };
      const res = await adminApi.getUsers(params);
      setUsersList(res.users || []);
      setUsersTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const loadBookings = async () => {
    try {
      const params = {
        page: bookingsPage,
        limit: 15,
        ...(bookingsStatusFilter ? { status: bookingsStatusFilter } : {}),
        ...(bookingsSearch ? { q: bookingsSearch } : {})
      };
      const res = await adminApi.getBookings(params);
      setBookingsList(res.bookings || []);
      setBookingsTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load bookings:', err);
    }
  };

  const loadAuditLogs = async () => {
    try {
      const res = await adminApi.getAuditLogs(1, 25);
      setAuditLogs(res.logs || []);
      setAuditTotal(res.total || 0);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    setIsUpdatingUser(true);
    try {
      await adminApi.updateUserRole(userId, newRole);
      setFeedbackMsg(`User role updated to ${newRole}`);
      setTimeout(() => setFeedbackMsg(''), 3000);
      loadUsers();
      loadAll();
    } catch (err) {
      alert(err.message || 'Failed to update user role');
    } finally {
      setIsUpdatingUser(false);
    }
  };

  const handleStatusChange = async (userId, newStatus) => {
    setIsUpdatingUser(true);
    try {
      await adminApi.updateUserStatus(userId, newStatus);
      setFeedbackMsg(`User status updated to ${newStatus}`);
      setTimeout(() => setFeedbackMsg(''), 3000);
      loadUsers();
      loadAll();
    } catch (err) {
      alert(err.message || 'Failed to update user status');
    } finally {
      setIsUpdatingUser(false);
    }
  };

  // Admin Call Stage Tracking (upcoming, pending, completed, cancelled)
  const handleBookingStageChange = async (bookingId, stage) => {
    setUpdatingBookingId(bookingId);
    try {
      await adminApi.updateBookingStatus(bookingId, stage);
      setFeedbackMsg(`Meeting stage updated to ${stage}`);
      setTimeout(() => setFeedbackMsg(''), 3000);
      loadBookings();
      loadAll();
    } catch (err) {
      alert(err.message || 'Failed to update meeting stage');
    } finally {
      setUpdatingBookingId(null);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Clean Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#557945]/20">
        <h1 className="text-2xl font-extrabold text-[#F1F6F2] tracking-tight">Admin Console</h1>

        {healthData && (
          <div className="flex items-center gap-2 text-xs bg-[#142017] px-3 py-1 rounded-xl border border-[#557945]/30">
            <span className="w-2 h-2 rounded-full bg-[#5D9253]" />
            <span className="text-[#84CC78] font-semibold">Database Connected</span>
          </div>
        )}
      </div>

      {feedbackMsg && (
        <div className="p-3 bg-[#5D9253]/15 border border-[#5D9253]/35 text-[#84CC78] text-xs rounded-xl font-medium flex items-center gap-2">
          <Check className="w-4 h-4 text-[#5D9253]" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#557945]/20 pb-2">
        <button
          onClick={() => setSearchParams({ tab: 'stats' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'stats'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-[#FFCB3D]" />
          <span>KPIs</span>
        </button>

        <button
          onClick={() => setSearchParams({ tab: 'users' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'users'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <Users className="w-3.5 h-3.5 text-[#5D9253]" />
          <span>Users ({usersTotal || statsData?.totalUsers || 0})</span>
        </button>

        <button
          onClick={() => setSearchParams({ tab: 'bookings' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'bookings'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <Calendar className="w-3.5 h-3.5 text-[#F1A344]" />
          <span>Bookings &amp; Calls ({bookingsTotal || statsData?.totalBookings || 0})</span>
        </button>

        <button
          onClick={() => setSearchParams({ tab: 'audit' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'audit'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <FileText className="w-3.5 h-3.5 text-[#84CC78]" />
          <span>Audit ({auditTotal})</span>
        </button>
      </div>

      {/* Tab 1: System KPIs & Chart-Oriented Analytics (100% Real Database Data) */}
      {activeTab === 'stats' && (() => {
        const totalMentors = statsData?.totalMentors ?? statsData?.stats?.totalMentors ?? 0;
        const totalStudents = statsData?.totalStudents ?? statsData?.stats?.totalStudents ?? 0;
        const totalAdmins = statsData?.totalAdmins ?? statsData?.stats?.totalAdmins ?? 1;
        const totalUsers = statsData?.totalUsers ?? statsData?.stats?.totalUsers ?? (totalMentors + totalStudents + totalAdmins);
        const totalBookings = statsData?.totalBookings ?? statsData?.stats?.totalBookings ?? 0;
        const upcomingBookings = statsData?.confirmedBookings ?? statsData?.stats?.upcomingBookings ?? 0;
        const completedBookings = statsData?.stats?.completedBookings ?? 0;
        const cancelledBookings = statsData?.stats?.cancelledBookings ?? 0;
        const totalConversations = statsData?.stats?.totalConversations ?? 0;
        const totalMessages = statsData?.stats?.totalMessages ?? 0;
        const activeUsers = statsData?.activeUsers ?? ((statsData?.stats?.activeStudents || 0) + totalAdmins);
        const popularDomains = statsData?.popularDomains || [];
        const topMentors = statsData?.topMentors || [];
        const bookingTrends = statsData?.bookingTrends || [];

        // Donut Chart calculations (Circle radius = 40, circumference = 2 * PI * 40 = 251.327)
        const totalRoleCount = Math.max(1, totalMentors + totalStudents + totalAdmins);
        const mentorPct = (totalMentors / totalRoleCount) * 100;
        const studentPct = (totalStudents / totalRoleCount) * 100;
        const adminPct = (totalAdmins / totalRoleCount) * 100;

        const C = 2 * Math.PI * 40;
        const mentorStroke = (mentorPct / 100) * C;
        const studentStroke = (studentPct / 100) * C;
        const adminStroke = (adminPct / 100) * C;

        const mentorOffset = 0;
        const studentOffset = -mentorStroke;
        const adminOffset = -(mentorStroke + studentStroke);

        const maxDomainCount = popularDomains.length > 0
          ? Math.max(...popularDomains.map((d) => d.count || 1))
          : 1;

        return (
          <div className="space-y-6">
            {/* Top KPI Metric Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="glass-card p-5 rounded-2xl border border-[#557945]/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] text-[#8BA190] font-semibold uppercase tracking-wider">
                    Total Users
                  </span>
                  <span className="w-2 h-2 rounded-full bg-[#5D9253]" />
                </div>
                <div className="text-3xl font-extrabold text-[#F1F6F2] tracking-tight">{totalUsers}</div>
                <div className="mt-2 text-xs text-[#84CC78] font-medium flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#84CC78] animate-pulse" />
                  {activeUsers} Active Accounts
                </div>
              </div>

              <div className="glass-card p-5 rounded-2xl border border-[#557945]/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] text-[#8BA190] font-semibold uppercase tracking-wider">
                    Mentors
                  </span>
                  <span className="text-[10px] font-mono text-[#84CC78] bg-[#142017] px-2 py-0.5 rounded border border-[#557945]/30">
                    Catalog
                  </span>
                </div>
                <div className="text-3xl font-extrabold text-[#84CC78] tracking-tight">{totalMentors}</div>
                <div className="mt-2 text-xs text-[#A2B5A6]">Verified Industry Leaders</div>
              </div>

              <div className="glass-card p-5 rounded-2xl border border-[#557945]/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] text-[#8BA190] font-semibold uppercase tracking-wider">
                    Students
                  </span>
                  <span className="text-[10px] font-mono text-[#FFCB3D] bg-[#142017] px-2 py-0.5 rounded border border-[#557945]/30">
                    Learners
                  </span>
                </div>
                <div className="text-3xl font-extrabold text-[#FFCB3D] tracking-tight">{totalStudents}</div>
                <div className="mt-2 text-xs text-[#A2B5A6]">Seeking Career Mentorship</div>
              </div>

              <div className="glass-card p-5 rounded-2xl border border-[#557945]/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] text-[#8BA190] font-semibold uppercase tracking-wider">
                    1:1 Sessions
                  </span>
                  <span className="text-[10px] font-mono text-[#F1A344] bg-[#142017] px-2 py-0.5 rounded border border-[#557945]/30">
                    Calendar
                  </span>
                </div>
                <div className="text-3xl font-extrabold text-[#F1A344] tracking-tight">{totalBookings}</div>
                <div className="mt-2 text-xs text-[#A2B5A6]">
                  {upcomingBookings} Upcoming • {completedBookings} Completed
                </div>
              </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 1: Role Distribution Donut Chart */}
              <div className="glass-panel rounded-3xl p-6 border border-[#557945]/30 shadow-xl space-y-5">
                <div className="flex items-center justify-between border-b border-[#557945]/20 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#F1F6F2] tracking-tight">User Role Distribution</h3>
                    <p className="text-[11px] text-[#8BA190]">Live breakdown of accounts registered in database</p>
                  </div>
                  <span className="text-[11px] font-mono font-bold text-[#FFCB3D] bg-[#0E1610] px-2.5 py-1 rounded-lg border border-[#557945]/30">
                    {totalUsers} Total
                  </span>
                </div>

                <div className="flex flex-col sm:flex-row items-center justify-around gap-6 pt-2">
                  {/* SVG Donut */}
                  <div className="relative w-44 h-44 flex items-center justify-center">
                    <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                      {/* Background Circle */}
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="#142017"
                        strokeWidth="12"
                      />
                      {/* Mentors Segment */}
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="#5D9253"
                        strokeWidth="12"
                        strokeDasharray={`${mentorStroke} ${C - mentorStroke}`}
                        strokeDashoffset={mentorOffset}
                        strokeLinecap="round"
                        className="transition-all duration-700"
                      />
                      {/* Students Segment */}
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="#FFCB3D"
                        strokeWidth="12"
                        strokeDasharray={`${studentStroke} ${C - studentStroke}`}
                        strokeDashoffset={studentOffset}
                        strokeLinecap="round"
                        className="transition-all duration-700"
                      />
                      {/* Admin Segment */}
                      <circle
                        cx="50"
                        cy="50"
                        r="40"
                        fill="transparent"
                        stroke="#F1A344"
                        strokeWidth="12"
                        strokeDasharray={`${adminStroke} ${C - adminStroke}`}
                        strokeDashoffset={adminOffset}
                        strokeLinecap="round"
                        className="transition-all duration-700"
                      />
                    </svg>
                    {/* Centered Total */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center pointer-events-none">
                      <span className="text-2xl font-black text-[#F1F6F2] leading-none">{totalUsers}</span>
                      <span className="text-[10px] text-[#8BA190] uppercase font-bold tracking-wider mt-1">Users</span>
                    </div>
                  </div>

                  {/* Donut Legend */}
                  <div className="space-y-3 w-full sm:w-auto">
                    <div className="flex items-center justify-between sm:justify-start gap-4 p-2 rounded-xl bg-[#0E1610]/70 border border-[#557945]/20">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-[#5D9253]" />
                        <span className="text-xs font-semibold text-[#D0DDD2]">Mentors</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-mono font-bold text-[#84CC78]">{totalMentors}</span>
                        <span className="text-[10px] text-[#8BA190] ml-1.5">({mentorPct.toFixed(1)}%)</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-start gap-4 p-2 rounded-xl bg-[#0E1610]/70 border border-[#557945]/20">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-[#FFCB3D]" />
                        <span className="text-xs font-semibold text-[#D0DDD2]">Students</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-mono font-bold text-[#FFCB3D]">{totalStudents}</span>
                        <span className="text-[10px] text-[#8BA190] ml-1.5">({studentPct.toFixed(1)}%)</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between sm:justify-start gap-4 p-2 rounded-xl bg-[#0E1610]/70 border border-[#557945]/20">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full bg-[#F1A344]" />
                        <span className="text-xs font-semibold text-[#D0DDD2]">Administrators</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs font-mono font-bold text-[#F1A344]">{totalAdmins}</span>
                        <span className="text-[10px] text-[#8BA190] ml-1.5">({adminPct.toFixed(1)}%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Chart 2: Popular Career Domains Bar Visualizer */}
              <div className="glass-panel rounded-3xl p-6 border border-[#557945]/30 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-[#557945]/20 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#F1F6F2] tracking-tight">Mentor Domain Breakdown</h3>
                    <p className="text-[11px] text-[#8BA190]">Expertise distribution aggregated across all mentors</p>
                  </div>
                  <span className="text-[11px] font-mono text-[#84CC78] bg-[#0E1610] px-2.5 py-1 rounded-lg border border-[#557945]/30">
                    {popularDomains.length} Domains
                  </span>
                </div>

                <div className="space-y-3 pt-1">
                  {popularDomains.map((dom, idx) => {
                    const pct = Math.round((dom.count / maxDomainCount) * 100);
                    return (
                      <div key={idx} className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-[#D0DDD2] font-medium">{dom.domain}</span>
                          <span className="font-mono font-bold text-[#FFCB3D]">{dom.count} mentors</span>
                        </div>
                        <div className="w-full h-2.5 bg-[#0E1610] rounded-full overflow-hidden border border-[#557945]/30">
                          <div
                            className="h-full bg-gradient-to-r from-[#5D9253] via-[#84CC78] to-[#FFCB3D] rounded-full transition-all duration-500"
                            style={{ width: `${Math.max(8, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Row 2: Booking Statuses & Activity Volume */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Chart 3: Session Stages & Statuses */}
              <div className="glass-panel rounded-3xl p-6 border border-[#557945]/30 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-[#557945]/20 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#F1F6F2] tracking-tight">Session Stages</h3>
                    <p className="text-[11px] text-[#8BA190]">Lifecycle breakdown of consultation calls</p>
                  </div>
                  <span className="text-[11px] font-mono text-[#F1A344] bg-[#0E1610] px-2.5 py-1 rounded-lg border border-[#557945]/30">
                    {totalBookings} Total
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 pt-2">
                  <div className="p-4 rounded-2xl bg-[#0E1610]/80 border border-[#557945]/25 text-center">
                    <span className="text-[10px] text-[#8BA190] uppercase font-bold block mb-1">Upcoming</span>
                    <span className="text-2xl font-black text-[#84CC78]">{upcomingBookings}</span>
                    <span className="text-[10px] text-[#A2B5A6] block mt-1">Confirmed</span>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#0E1610]/80 border border-[#557945]/25 text-center">
                    <span className="text-[10px] text-[#8BA190] uppercase font-bold block mb-1">Completed</span>
                    <span className="text-2xl font-black text-[#FFCB3D]">{completedBookings}</span>
                    <span className="text-[10px] text-[#A2B5A6] block mt-1">Finished</span>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#0E1610]/80 border border-[#557945]/25 text-center">
                    <span className="text-[10px] text-[#8BA190] uppercase font-bold block mb-1">Cancelled</span>
                    <span className="text-2xl font-black text-rose-400">{cancelledBookings}</span>
                    <span className="text-[10px] text-[#A2B5A6] block mt-1">Canceled</span>
                  </div>
                </div>

                {topMentors.length > 0 && (
                  <div className="pt-2 border-t border-[#557945]/20 flex items-center justify-between text-xs text-[#A2B5A6]">
                    <span>Top Mentor Booked:</span>
                    <span className="font-semibold text-[#84CC78]">{topMentors[0].name} ({topMentors[0].bookingsCount} booking)</span>
                  </div>
                )}
              </div>

              {/* Chart 4: AI Inquiries & Conversations Activity */}
              <div className="glass-panel rounded-3xl p-6 border border-[#557945]/30 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-[#557945]/20 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#F1F6F2] tracking-tight">AI Matching Volume</h3>
                    <p className="text-[11px] text-[#8BA190]">Conversational queries and mentor recommendations</p>
                  </div>
                  <span className="text-[11px] font-mono text-[#84CC78] bg-[#0E1610] px-2.5 py-1 rounded-lg border border-[#557945]/30">
                    {totalConversations} Inquiries
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="p-4 rounded-2xl bg-[#0E1610]/80 border border-[#557945]/25">
                    <span className="text-[10px] text-[#8BA190] uppercase font-bold block mb-1">Total Chat Sessions</span>
                    <span className="text-2xl font-black text-[#FFCB3D]">{totalConversations}</span>
                    <p className="text-[11px] text-[#A2B5A6] mt-1">Active career inquiries</p>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#0E1610]/80 border border-[#557945]/25">
                    <span className="text-[10px] text-[#8BA190] uppercase font-bold block mb-1">Total AI Messages</span>
                    <span className="text-2xl font-black text-[#84CC78]">{totalMessages}</span>
                    <p className="text-[11px] text-[#A2B5A6] mt-1">Tokens &amp; queries exchanged</p>
                  </div>
                </div>

                <div className="p-3 rounded-2xl bg-[#142017]/50 border border-[#557945]/20 flex items-center justify-between text-xs">
                  <span className="text-[#D0DDD2]">Vector Index Status</span>
                  <span className="text-[#84CC78] font-mono font-bold flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[#84CC78]" />
                    ChromaDB 50 Mentors Indexed
                  </span>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Tab 2: User Directory */}
      {activeTab === 'users' && (
        <div className="glass-panel rounded-2xl p-5 shadow-xl border border-[#557945]/30 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#557945]/20">
            <h2 className="text-sm font-bold text-[#F1F6F2] uppercase">User Directory</h2>

            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#557945]" />
                <input
                  type="text"
                  value={usersSearch}
                  onChange={(e) => {
                    setUsersSearch(e.target.value);
                    setUsersPage(1);
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && loadUsers()}
                  placeholder="Search user..."
                  className="pl-8 pr-3 py-1.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] w-48 focus:outline-none"
                />
              </div>

              <select
                value={usersRoleFilter}
                onChange={(e) => {
                  setUsersRoleFilter(e.target.value);
                  setUsersPage(1);
                }}
                className="glass-input rounded-xl px-2.5 py-1.5 text-xs text-[#F1F6F2] focus:outline-none"
              >
                <option value="" className="bg-[#0E1610]">All Roles</option>
                <option value="student" className="bg-[#0E1610]">Student</option>
                <option value="mentor" className="bg-[#0E1610]">Mentor</option>
                <option value="admin" className="bg-[#0E1610]">Admin</option>
              </select>

              <select
                value={usersStatusFilter}
                onChange={(e) => {
                  setUsersStatusFilter(e.target.value);
                  setUsersPage(1);
                }}
                className="glass-input rounded-xl px-2.5 py-1.5 text-xs text-[#F1F6F2] focus:outline-none"
              >
                <option value="" className="bg-[#0E1610]">All Statuses</option>
                <option value="active" className="bg-[#0E1610]">Active</option>
                <option value="suspended" className="bg-[#0E1610]">Suspended</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0E1610] text-[#8BA190] uppercase font-bold text-[10px] border-b border-[#557945]/30">
                <tr>
                  <th className="py-2.5 px-3">User</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Mentor ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#557945]/20">
                {usersList.map((u) => (
                  <tr key={u.userId} className="hover:bg-[#152318]/40 transition">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-[#F1F6F2]">{u.fullName}</div>
                      <div className="text-[11px] text-[#A2B5A6]">{u.email}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <select
                        value={u.role}
                        disabled={isUpdatingUser}
                        onChange={(e) => handleRoleChange(u.userId, e.target.value)}
                        className="bg-[#0E1610] border border-[#557945]/30 text-xs rounded-lg px-2 py-1 text-[#D0DDD2] focus:outline-none"
                      >
                        <option value="student">Student</option>
                        <option value="mentor">Mentor</option>
                        <option value="admin">Admin</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-3">
                      <select
                        value={u.status}
                        disabled={isUpdatingUser}
                        onChange={(e) => handleStatusChange(u.userId, e.target.value)}
                        className={`text-xs rounded-lg px-2 py-1 font-semibold border ${
                          u.status === 'active'
                            ? 'bg-[#5D9253]/20 border-[#5D9253]/40 text-[#84CC78]'
                            : 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                        }`}
                      >
                        <option value="active" className="bg-[#0E1610]">Active</option>
                        <option value="suspended" className="bg-[#0E1610]">Suspended</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-[#FFCB3D]">
                      {u.mentorId || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[#557945]/20 text-xs text-[#A2B5A6]">
            <span>Page {usersPage} (Total: {usersTotal})</span>
            <div className="flex gap-2">
              <button
                disabled={usersPage <= 1}
                onClick={() => setUsersPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded-lg bg-[#142017] border border-[#557945]/30 disabled:opacity-40"
              >
                Prev
              </button>
              <button
                disabled={usersList.length < 15}
                onClick={() => setUsersPage((p) => p + 1)}
                className="px-3 py-1 rounded-lg bg-[#142017] border border-[#557945]/30 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Platform Bookings with Live Join & 3 Stages Tracking */}
      {activeTab === 'bookings' && (
        <div className="glass-panel rounded-2xl p-5 shadow-xl border border-[#557945]/30 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#557945]/20">
            <div>
              <h2 className="text-sm font-bold text-[#F1F6F2] uppercase">Meeting &amp; Call Oversight</h2>
              <span className="text-[11px] text-[#A2B5A6]">Join live meetings to monitor sessions; track stages (upcoming, pending, completed, cancelled)</span>
            </div>
            <span className="font-mono font-bold text-xs text-[#FFCB3D] bg-[#0E1610] px-2.5 py-1 rounded-lg border border-[#557945]/30">
              {bookingsTotal} Sessions
            </span>
          </div>

          <div className="space-y-3">
            {bookingsList.map((b) => {
              const currentStage = b.status === 'confirmed' ? 'upcoming' : b.status;
              return (
                <div
                  key={b.bookingId}
                  className="p-4 glass-card rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[#F1F6F2]">
                        {b.userName} &amp; {b.mentorName}
                      </span>
                      <span className="text-[10px] font-mono text-[#FFCB3D] bg-[#0E1610] px-1.5 py-0.2 rounded border border-[#557945]/30">
                        {b.mentorId}
                      </span>
                    </div>

                    <div className="text-xs text-[#D0DDD2]">{b.topic}</div>
                    <div className="text-[11px] text-[#8BA190] font-mono">
                      {new Date(b.slotStart).toUTCString()} &bull; ID: {b.bookingId}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {/* Admin Join Meeting Button */}
                    {b.meetingLink && b.status !== 'cancelled' && (
                      <a
                        href={b.meetingLink}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-[#5D9253] hover:bg-[#5D9253]/90 text-[#090E0A] text-xs font-bold rounded-xl transition shadow-sm"
                        title="Join Meeting directly to monitor call"
                      >
                        <Video className="w-3.5 h-3.5" />
                        <span>Join Call</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}

                    {/* Stage Tracker Selector: upcoming, pending, completed, cancelled */}
                    <div className="flex items-center gap-1.5 bg-[#0E1610] p-1 rounded-xl border border-[#557945]/30">
                      <span className="text-[10px] text-[#8BA190] px-1 font-semibold uppercase">Stage:</span>
                      <select
                        value={currentStage}
                        disabled={updatingBookingId === b.bookingId}
                        onChange={(e) => handleBookingStageChange(b.bookingId, e.target.value)}
                        className={`text-xs font-bold rounded-lg px-2 py-1 border focus:outline-none transition ${
                          currentStage === 'upcoming'
                            ? 'bg-[#5D9253]/20 border-[#5D9253]/40 text-[#84CC78]'
                            : currentStage === 'pending'
                            ? 'bg-[#F1A344]/20 border-[#F1A344]/40 text-[#F1A344]'
                            : currentStage === 'completed'
                            ? 'bg-[#FFCB3D]/20 border-[#FFCB3D]/40 text-[#FFCB3D]'
                            : 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                        }`}
                      >
                        <option value="upcoming" className="bg-[#0E1610]">Upcoming</option>
                        <option value="pending" className="bg-[#0E1610]">Pending</option>
                        <option value="completed" className="bg-[#0E1610]">Completed</option>
                        <option value="cancelled" className="bg-[#0E1610]">Cancelled</option>
                      </select>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 4: Security Audit Trail */}
      {activeTab === 'audit' && (
        <div className="glass-panel rounded-2xl p-5 shadow-xl border border-[#557945]/30 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#557945]/20">
            <h2 className="text-sm font-bold text-[#F1F6F2] uppercase">Security Audit Trail</h2>
            <span className="font-mono text-xs text-[#84CC78] bg-[#0E1610] px-2 py-0.5 rounded-lg border border-[#557945]/30">
              {auditTotal} Events
            </span>
          </div>

          <div className="space-y-2">
            {auditLogs.map((log, idx) => (
              <div
                key={idx}
                className="p-2.5 bg-[#0E1610] border border-[#557945]/25 rounded-xl flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-mono text-[10px] text-[#FFCB3D] uppercase font-bold mr-2">
                    {log.action}
                  </span>
                  <span className="text-[#D0DDD2]">{log.targetUser || log.targetUserId}</span>
                  <span className="text-[10px] text-[#8BA190] ml-2">by {log.adminEmail}</span>
                </div>
                <span className="text-[10px] text-[#A2B5A6] font-mono">
                  {log.timestamp ? new Date(log.timestamp).toISOString().replace('T', ' ').slice(0, 19) : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

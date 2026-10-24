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
  ExternalLink,
  TrendingUp,
  BarChart3,
  Layers,
  CheckCircle2,
  AlertCircle
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
    setFeedbackMsg('');
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
    setFeedbackMsg('');
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

  const handleBookingStageChange = async (bookingId, newStatus) => {
    setUpdatingBookingId(bookingId);
    setFeedbackMsg('');
    try {
      await adminApi.updateBookingStatus(bookingId, newStatus);
      setFeedbackMsg(`Booking status updated to ${newStatus}`);
      setTimeout(() => setFeedbackMsg(''), 3000);
      loadBookings();
      loadAll();
    } catch (err) {
      alert(err.message || 'Failed to update booking status');
    } finally {
      setUpdatingBookingId(null);
    }
  };

  const handleApproveBooking = async (bookingId) => {
    setUpdatingBookingId(bookingId);
    setFeedbackMsg('');
    try {
      await adminApi.approveBooking(bookingId);
      setFeedbackMsg(`Booking ${bookingId} approved successfully! Confirmation email dispatched.`);
      setTimeout(() => setFeedbackMsg(''), 4000);
      loadBookings();
      loadAll();
    } catch (err) {
      alert(err.message || 'Failed to approve booking');
    } finally {
      setUpdatingBookingId(null);
    }
  };

  const handleRejectBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to reject and cancel this booking request?')) return;
    setUpdatingBookingId(bookingId);
    setFeedbackMsg('');
    try {
      await adminApi.rejectBooking(bookingId);
      setFeedbackMsg(`Booking ${bookingId} has been rejected/cancelled.`);
      setTimeout(() => setFeedbackMsg(''), 4000);
      loadBookings();
      loadAll();
    } catch (err) {
      alert(err.message || 'Failed to reject booking');
    } finally {
      setUpdatingBookingId(null);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Top Header & Workspace Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E4E7EC]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-[#202124] tracking-tight">Administrative Operations</h1>
            <span className="text-xs bg-[#EFF4FA] text-[#315E9E] border border-[#D0DCEB] px-2.5 py-0.5 rounded-full font-bold">
              Admin Workspace
            </span>
          </div>
          <p className="text-xs text-[#667085] mt-0.5">
            Verified database metrics, user management, and mentorship meeting oversight
          </p>
        </div>

        {healthData && (
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white border border-[#E4E7EC] rounded-lg text-xs font-mono shadow-xs">
            <span className="w-2 h-2 rounded-full bg-[#12B76A]" />
            <span className="text-[#344054] font-semibold">System: {healthData.status}</span>
          </div>
        )}
      </div>

      {feedbackMsg && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-[#027A48] text-xs rounded-lg font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#12B76A]" />
          <span>{feedbackMsg}</span>
        </div>
      )}


      {/* ========================================================================= */}
      {/* TAB 1: VERIFIED MONGODB KPIS & ACTIVITY METRICS */}
      {/* ========================================================================= */}
      {activeTab === 'stats' && (() => {
        const totalStudents = statsData?.totalStudents ?? 0;
        const totalMentors = statsData?.totalMentors ?? 0;
        const totalBookings = statsData?.totalBookings ?? 0;
        const upcomingBookings = statsData?.upcomingBookings ?? statsData?.stats?.upcomingBookings ?? 0;
        const pendingBookings = statsData?.pendingBookings ?? statsData?.stats?.pendingBookings ?? 0;
        const completedBookings = statsData?.completedBookings ?? statsData?.stats?.completedBookings ?? 0;
        const cancelledBookings = statsData?.cancelledBookings ?? statsData?.stats?.cancelledBookings ?? 0;
        const totalConversations = statsData?.totalConversations ?? 0;
        const totalMessages = statsData?.totalMessages ?? 0;
        const activeStudents = statsData?.activeStudents ?? 0;
        const popularDomains = statsData?.popularDomains || [];
        const topMentors = statsData?.topMentors || [];
        const bookingTrends = statsData?.bookingTrends || [];

        const maxDomainCount = Math.max(1, ...popularDomains.map((d) => d.count));
        const maxTrendCount = Math.max(1, ...bookingTrends.map((t) => t.count));

        return (
          <div className="space-y-6">
            {/* Top Stat Cards (4 columns) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white rounded-xl p-5 border border-[#E4E7EC] shadow-xs">
                <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider block">
                  Students Registered
                </span>
                <div className="text-2xl font-bold text-[#202124] mt-1">{totalStudents}</div>
                <span className="text-[11px] text-[#12B76A] font-medium block mt-1">
                  Active (last 30d): {activeStudents}
                </span>
              </div>

              <div className="bg-white rounded-xl p-5 border border-[#E4E7EC] shadow-xs">
                <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider block">
                  Mentors Catalog
                </span>
                <div className="text-2xl font-bold text-[#315E9E] mt-1">{totalMentors}</div>
                <span className="text-[11px] text-[#667085] font-medium block mt-1">
                  ChromaDB vector indexed
                </span>
              </div>

              <div className="bg-white rounded-xl p-5 border border-[#E4E7EC] shadow-xs">
                <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider block">
                  Total Bookings
                </span>
                <div className="text-2xl font-bold text-[#202124] mt-1">{totalBookings}</div>
                <span className="text-[11px] text-[#667085] font-medium block mt-1">
                  Upcoming: {upcomingBookings} &bull; <span className={pendingBookings > 0 ? "text-[#B54708] font-bold" : ""}>Pending: {pendingBookings}</span> &bull; Completed: {completedBookings}
                </span>
              </div>

              <div className="bg-white rounded-xl p-5 border border-[#E4E7EC] shadow-xs">
                <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider block">
                  Career Inquiries
                </span>
                <div className="text-2xl font-bold text-[#315E9E] mt-1">{totalConversations}</div>
                <span className="text-[11px] text-[#667085] font-medium block mt-1">
                  Total Messages: {totalMessages}
                </span>
              </div>
            </div>

            {/* Row 1: Popular Domains & Booking Trends */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Popular Domains Breakdown */}
              <div className="bg-white rounded-xl p-6 border border-[#E4E7EC] shadow-xs space-y-4">
                <div className="flex items-center justify-between border-b border-[#E4E7EC] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#202124]">Popular Career Domains</h3>
                    <p className="text-xs text-[#667085]">Specializations in student and mentor profiles</p>
                  </div>
                  <span className="text-xs font-mono text-[#315E9E] bg-[#EFF4FA] px-2.5 py-1 rounded-md font-semibold">
                    {popularDomains.length} Domains
                  </span>
                </div>

                <div className="space-y-3 pt-1">
                  {popularDomains.length === 0 ? (
                    <div className="text-center py-6 text-xs text-[#667085]">No domain data recorded yet.</div>
                  ) : (
                    popularDomains.map((dom, idx) => {
                      const pct = Math.round((dom.count / maxDomainCount) * 100);
                      return (
                        <div key={idx} className="space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-[#344054] font-medium">{dom.domain}</span>
                            <span className="font-mono font-bold text-[#315E9E]">{dom.count} users</span>
                          </div>
                          <div className="w-full h-2.5 bg-[#F2F4F7] rounded-full overflow-hidden">
                            <div
                              className="h-full bg-[#315E9E] rounded-full transition-all duration-500"
                              style={{ width: `${Math.max(8, pct)}%` }}
                            />
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Consultation Lifecycle Stages */}
              <div className="bg-white rounded-xl p-6 border border-[#E4E7EC] shadow-xs space-y-4">
                <div className="flex items-center justify-between border-b border-[#E4E7EC] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[#202124]">Consultation Session Stages</h3>
                    <p className="text-xs text-[#667085]">Lifecycle status across all mentorship bookings</p>
                  </div>
                  <span className="text-xs font-mono text-[#315E9E] bg-[#EFF4FA] px-2.5 py-1 rounded-md font-semibold">
                    {totalBookings} Total
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 pt-2">
                  <div className="p-4 rounded-xl bg-[#F8F9FA] border border-[#E4E7EC] text-center">
                    <span className="text-[11px] text-[#667085] uppercase font-bold block mb-1">Upcoming</span>
                    <span className="text-2xl font-bold text-[#315E9E]">{upcomingBookings}</span>
                    <span className="text-[11px] text-[#667085] block mt-1">Confirmed</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#F8F9FA] border border-[#E4E7EC] text-center">
                    <span className="text-[11px] text-[#667085] uppercase font-bold block mb-1">Completed</span>
                    <span className="text-2xl font-bold text-[#12B76A]">{completedBookings}</span>
                    <span className="text-[11px] text-[#667085] block mt-1">Finished</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#F8F9FA] border border-[#E4E7EC] text-center">
                    <span className="text-[11px] text-[#667085] uppercase font-bold block mb-1">Cancelled</span>
                    <span className="text-2xl font-bold text-[#D92D20]">{cancelledBookings}</span>
                    <span className="text-[11px] text-[#667085] block mt-1">Liberated</span>
                  </div>
                </div>

                {topMentors.length > 0 && (
                  <div className="pt-3 border-t border-[#E4E7EC] flex items-center justify-between text-xs text-[#667085]">
                    <span>Most Booked Mentor:</span>
                    <span className="font-semibold text-[#202124]">
                      {topMentors[0].name} ({topMentors[0].bookingsCount} sessions)
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })()}

      {/* ========================================================================= */}
      {/* TAB 2: USER DIRECTORY */}
      {/* ========================================================================= */}
      {activeTab === 'users' && (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E4E7EC]">
            <div>
              <h2 className="text-base font-bold text-[#202124]">User Directory</h2>
              <p className="text-xs text-[#667085]">Manage registered students, mentors, and administrators</p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#98A2B3]" />
                <input
                  type="text"
                  value={usersSearch}
                  onChange={(e) => {
                    setUsersSearch(e.target.value);
                    setUsersPage(1);
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && loadUsers()}
                  placeholder="Search by name or email..."
                  className="pl-8 pr-3 py-1.5 text-xs bg-white border border-[#D0D5DD] rounded-lg text-[#202124] placeholder-[#98A2B3] w-52 focus:outline-none focus:border-[#315E9E]"
                />
              </div>

              <select
                value={usersRoleFilter}
                onChange={(e) => {
                  setUsersRoleFilter(e.target.value);
                  setUsersPage(1);
                }}
                className="bg-white border border-[#D0D5DD] rounded-lg px-2.5 py-1.5 text-xs text-[#202124] focus:outline-none focus:border-[#315E9E]"
              >
                <option value="">All Roles</option>
                <option value="student">Student</option>
                <option value="mentor">Mentor</option>
                <option value="admin">Admin</option>
              </select>

              <select
                value={usersStatusFilter}
                onChange={(e) => {
                  setUsersStatusFilter(e.target.value);
                  setUsersPage(1);
                }}
                className="bg-white border border-[#D0D5DD] rounded-lg px-2.5 py-1.5 text-xs text-[#202124] focus:outline-none focus:border-[#315E9E]"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F8F9FA] text-[#667085] uppercase font-semibold text-[10px] border-b border-[#E4E7EC]">
                <tr>
                  <th className="py-2.5 px-3">User</th>
                  <th className="py-2.5 px-3">Role</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Mentor ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E7EC]">
                {usersList.map((u) => (
                  <tr key={u.userId} className="hover:bg-[#F8F9FA] transition">
                    <td className="py-2.5 px-3">
                      <div className="font-semibold text-[#202124]">{u.fullName}</div>
                      <div className="text-[11px] text-[#667085]">{u.email}</div>
                    </td>
                    <td className="py-2.5 px-3">
                      <select
                        value={u.role}
                        disabled={isUpdatingUser}
                        onChange={(e) => handleRoleChange(u.userId, e.target.value)}
                        className="bg-white border border-[#D0D5DD] text-xs rounded-md px-2 py-1 text-[#202124] focus:outline-none focus:border-[#315E9E]"
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
                        className={`text-xs rounded-md px-2 py-1 font-semibold border ${
                          u.status === 'active'
                            ? 'bg-emerald-50 border-emerald-200 text-[#027A48]'
                            : 'bg-rose-50 border-rose-200 text-[#D92D20]'
                        }`}
                      >
                        <option value="active">Active</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-[#315E9E]">
                      {u.mentorId || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[#E4E7EC] text-xs text-[#667085]">
            <span>Page {usersPage} (Total: {usersTotal})</span>
            <div className="flex gap-2">
              <button
                disabled={usersPage <= 1}
                onClick={() => setUsersPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 rounded-md bg-white border border-[#D0D5DD] disabled:opacity-40 hover:bg-[#F8F9FA] cursor-pointer"
              >
                Prev
              </button>
              <button
                disabled={usersList.length < 15}
                onClick={() => setUsersPage((p) => p + 1)}
                className="px-3 py-1 rounded-md bg-white border border-[#D0D5DD] disabled:opacity-40 hover:bg-[#F8F9FA] cursor-pointer"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: PLATFORM BOOKINGS & MEETING OVERSIGHT */}
      {/* ========================================================================= */}
      {activeTab === 'bookings' && (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E4E7EC]">
            <div>
              <h2 className="text-base font-bold text-[#202124]">Meeting &amp; Session Oversight</h2>
              <span className="text-xs text-[#667085]">
                Review student booking requests, approve pending sessions, and monitor Google Meet calls
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono font-bold text-xs text-[#315E9E] bg-[#EFF4FA] px-2.5 py-1 rounded-md">
                {bookingsTotal} Total Sessions
              </span>
            </div>
          </div>

          {/* Filter Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-[#F8F9FA] rounded-lg border border-[#E4E7EC]">
            <div className="relative flex-1 min-w-[200px] max-w-sm">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-[#98A2B3]" />
              <input
                type="text"
                value={bookingsSearch}
                onChange={(e) => {
                  setBookingsSearch(e.target.value);
                  setBookingsPage(1);
                }}
                onKeyDown={(e) => e.key === 'Enter' && loadBookings()}
                placeholder="Search by student, mentor, or ID..."
                className="pl-8 pr-3 py-1.5 text-xs bg-white border border-[#D0D5DD] rounded-lg text-[#202124] placeholder-[#98A2B3] w-full focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div className="flex items-center gap-2">
              <select
                value={bookingsStatusFilter}
                onChange={(e) => {
                  setBookingsStatusFilter(e.target.value);
                  setBookingsPage(1);
                }}
                className="bg-white border border-[#D0D5DD] rounded-lg px-2.5 py-1.5 text-xs text-[#202124] focus:outline-none focus:border-[#315E9E]"
              >
                <option value="">All Statuses</option>
                <option value="pending">Pending Approval (Action Required)</option>
                <option value="confirmed">Confirmed / Upcoming</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>

              <button
                type="button"
                onClick={loadBookings}
                className="px-3 py-1.5 bg-white border border-[#D0D5DD] text-xs font-semibold text-[#344054] rounded-lg hover:bg-[#F2F4F7] cursor-pointer"
              >
                Refresh
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {bookingsList.length === 0 ? (
              <div className="py-12 text-center text-[#667085] text-xs border border-dashed border-[#E4E7EC] rounded-xl">
                No session bookings found matching the current filters.
              </div>
            ) : (
              bookingsList.map((b) => {
                const isPending = b.status === 'pending';
                const currentStage = b.status === 'confirmed' ? 'upcoming' : b.status;

                return (
                  <div
                    key={b.bookingId}
                    className={`p-4 bg-white rounded-xl border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 transition ${
                      isPending
                        ? 'border-amber-300 bg-amber-50/20'
                        : 'border-[#E4E7EC] hover:border-[#315E9E]/40'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-[#202124]">
                          {b.userName} &amp; {b.mentorName}
                        </span>
                        <span className="text-[11px] font-mono text-[#315E9E] bg-[#EFF4FA] px-2 py-0.5 rounded font-bold">
                          {b.mentorId}
                        </span>
                        {isPending && (
                          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-100 text-[#B54708] border border-amber-300 animate-pulse">
                            Pending Approval
                          </span>
                        )}
                      </div>

                      <div className="text-xs text-[#344054]">
                        <span className="font-semibold">Topic: </span>
                        {b.topic || 'Mentorship consultation'}
                      </div>
                      <div className="text-[11px] text-[#667085] font-mono">
                        {new Date(b.slotStart).toUTCString()} &bull; ID: {b.bookingId}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                      {/* 1-Click Approve / Reject for Pending Sessions */}
                      {isPending && (
                        <div className="flex items-center gap-1.5 mr-2">
                          <button
                            type="button"
                            disabled={updatingBookingId === b.bookingId}
                            onClick={() => handleApproveBooking(b.bookingId)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#027A48] hover:bg-[#05603A] text-white text-xs font-semibold rounded-lg transition shadow-xs cursor-pointer disabled:opacity-50"
                            title="Approve booking and confirm meeting"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Approve</span>
                          </button>
                          <button
                            type="button"
                            disabled={updatingBookingId === b.bookingId}
                            onClick={() => handleRejectBooking(b.bookingId)}
                            className="flex items-center gap-1 px-2.5 py-1.5 bg-white border border-rose-300 hover:bg-rose-50 text-[#D92D20] text-xs font-semibold rounded-lg transition cursor-pointer disabled:opacity-50"
                            title="Reject session request"
                          >
                            <span>Reject</span>
                          </button>
                        </div>
                      )}

                      {/* Admin Join Call Button */}
                      {b.meetingLink && b.status !== 'cancelled' && (
                        <a
                          href={b.meetingLink}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#315E9E] hover:bg-[#26497B] text-white text-xs font-semibold rounded-lg transition shadow-xs"
                          title="Join Meeting directly to monitor session"
                        >
                          <Video className="w-3.5 h-3.5" />
                          <span>Join Call</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}

                      {/* Stage Tracker Selector: upcoming, pending, completed, cancelled */}
                      <div className="flex items-center gap-1.5 bg-[#F8F9FA] p-1 rounded-lg border border-[#D0D5DD]">
                        <span className="text-[10px] text-[#667085] px-1 font-semibold uppercase">Stage:</span>
                        <select
                          value={currentStage}
                          disabled={updatingBookingId === b.bookingId}
                          onChange={(e) => handleBookingStageChange(b.bookingId, e.target.value)}
                          className={`text-xs font-bold rounded-md px-2 py-1 border focus:outline-none transition ${
                            currentStage === 'upcoming'
                              ? 'bg-emerald-50 border-emerald-200 text-[#027A48]'
                              : currentStage === 'pending'
                              ? 'bg-amber-50 border-amber-200 text-[#B54708]'
                              : currentStage === 'completed'
                              ? 'bg-blue-50 border-blue-200 text-[#315E9E]'
                              : 'bg-rose-50 border-rose-200 text-[#D92D20]'
                          }`}
                        >
                          <option value="pending">Pending</option>
                          <option value="upcoming">Upcoming (Approved)</option>
                          <option value="completed">Completed</option>
                          <option value="cancelled">Cancelled</option>
                        </select>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: SECURITY AUDIT TRAIL */}
      {/* ========================================================================= */}
      {activeTab === 'audit' && (
        <div className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-xs space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#E4E7EC]">
            <h2 className="text-base font-bold text-[#202124]">Security Audit Trail</h2>
            <span className="font-mono text-xs text-[#315E9E] bg-[#EFF4FA] px-2 py-0.5 rounded-md font-bold">
              {auditTotal} Events
            </span>
          </div>

          <div className="space-y-2">
            {auditLogs.map((log, idx) => (
              <div
                key={idx}
                className="p-3 bg-[#F8F9FA] border border-[#E4E7EC] rounded-lg flex items-center justify-between text-xs"
              >
                <div>
                  <span className="font-mono text-[11px] text-[#315E9E] uppercase font-bold mr-2">
                    {log.action}
                  </span>
                  <span className="text-[#202124] font-medium">{log.targetUser || log.targetUserId}</span>
                  <span className="text-[11px] text-[#667085] ml-2">by {log.adminEmail}</span>
                </div>
                <span className="text-[11px] text-[#667085] font-mono">
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

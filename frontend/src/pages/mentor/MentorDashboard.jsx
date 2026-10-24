import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { mentorApi, getMentorPassword } from '../../services/api';
import {
  Calendar,
  Clock,
  Video,
  ExternalLink,
  FileText,
  UserCheck,
  Save,
  CheckCircle2,
  X,
  Mail
} from 'lucide-react';

export default function MentorDashboard() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'sessions';

  const [dashboardData, setDashboardData] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [selectedContext, setSelectedContext] = useState(null);
  const [loadingContext, setLoadingContext] = useState(false);
  const [updatingBookingId, setUpdatingBookingId] = useState(null);
  const [statusFeedback, setStatusFeedback] = useState('');

  // Mentor Profile State (including editable email)
  const [mentorProfile, setMentorProfile] = useState({
    email: user?.email || '',
    company: '',
    role: '',
    domain: '',
    city: '',
    seniority: 'Senior'
  });
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState('');

  useEffect(() => {
    loadDashboard();
    loadBookings();
    loadProfile();
  }, [user]);

  const loadDashboard = async () => {
    try {
      const data = await mentorApi.getDashboard();
      setDashboardData(data);
    } catch (err) {
      console.error('Failed to load mentor dashboard:', err);
    }
  };

  const loadBookings = async () => {
    try {
      const data = await mentorApi.getBookings();
      setBookings(data || []);
    } catch (err) {
      console.error('Failed to load mentor bookings:', err);
    }
  };

  const loadProfile = async () => {
    try {
      const profile = await mentorApi.getProfile();
      if (profile) {
        setMentorProfile({
          email: profile.email || user?.email || '',
          company: profile.company || '',
          role: profile.role || '',
          domain: profile.domain || '',
          city: profile.city || '',
          seniority: profile.seniority || 'Senior'
        });
      }
    } catch (err) {
      console.error('Failed to load mentor profile:', err);
    }
  };

  const handleViewStudentContext = async (bookingId) => {
    setLoadingContext(true);
    setSelectedContext(null);
    try {
      const ctx = await mentorApi.getStudentContext(bookingId);
      setSelectedContext(ctx);
    } catch (err) {
      alert(err.message || 'Failed to retrieve authorized student context');
    } finally {
      setLoadingContext(false);
    }
  };

  const handleUpdateStatus = async (bookingId, newStatus) => {
    setUpdatingBookingId(bookingId);
    setStatusFeedback('');
    try {
      await mentorApi.updateStatus(bookingId, newStatus);
      setStatusFeedback(`Status updated to ${newStatus}`);
      setTimeout(() => setStatusFeedback(''), 3000);
      loadBookings();
      loadDashboard();
    } catch (err) {
      alert(err.message || 'Failed to update status');
    } finally {
      setUpdatingBookingId(null);
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setProfileSaving(true);
    setProfileError('');
    try {
      await mentorApi.updateProfile(mentorProfile);
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
      loadDashboard();
    } catch (err) {
      setProfileError(err.message || 'Failed to update profile');
    } finally {
      setProfileSaving(false);
    }
  };

  const currentMentorId = dashboardData?.mentorId || user.mentorId || 'MENTOR';

  return (
    <div className="space-y-6 font-sans">
      {/* Clean Header & Real Metrics */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#557945]/20">
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-extrabold text-[#F1F6F2] tracking-tight">Mentor Portal</h1>
          <span className="text-[11px] bg-[#5D9253]/20 text-[#84CC78] border border-[#5D9253]/40 px-2 py-0.5 rounded-lg font-mono font-bold">
            {currentMentorId}
          </span>
        </div>

        {/* Real Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="glass-card px-4 py-2 rounded-2xl">
            <span className="text-[10px] text-[#8BA190] font-semibold uppercase block">Upcoming</span>
            <span className="text-base font-bold text-[#84CC78]">{dashboardData?.stats?.upcomingSessions || 0}</span>
          </div>
          <div className="glass-card px-4 py-2 rounded-2xl">
            <span className="text-[10px] text-[#8BA190] font-semibold uppercase block">Completed</span>
            <span className="text-base font-bold text-[#FFCB3D]">{dashboardData?.stats?.completedSessions || 0}</span>
          </div>
          <div className="glass-card px-4 py-2 rounded-2xl">
            <span className="text-[10px] text-[#8BA190] font-semibold uppercase block">Total</span>
            <span className="text-base font-bold text-[#F1A344]">{bookings.length}</span>
          </div>
        </div>
      </div>

      {statusFeedback && (
        <div className="p-3 bg-[#5D9253]/15 border border-[#5D9253]/35 text-[#84CC78] text-xs rounded-xl font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#5D9253]" />
          <span>{statusFeedback}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-[#557945]/20 pb-2">
        <button
          onClick={() => setSearchParams({ tab: 'sessions' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'sessions'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <Calendar className="w-3.5 h-3.5 text-[#5D9253]" />
          <span>My Sessions ({bookings.length})</span>
        </button>

        <button
          onClick={() => setSearchParams({ tab: 'profile' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'profile'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <UserCheck className="w-3.5 h-3.5 text-[#5D9253]" />
          <span>Profile &amp; Email</span>
        </button>
      </div>

      {/* Tab 1: Sessions List & Student Context */}
      {activeTab === 'sessions' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 glass-panel rounded-2xl p-5 shadow-xl space-y-3">
            <h2 className="text-xs font-bold text-[#F1F6F2] uppercase tracking-wider mb-2">
              Scheduled Sessions
            </h2>

            {bookings.length === 0 ? (
              <div className="text-center py-12 text-[#8BA190] text-xs border border-dashed border-[#557945]/30 rounded-2xl p-6">
                No bookings scheduled yet for {currentMentorId}.
              </div>
            ) : (
              <div className="space-y-3">
                {bookings.map((booking) => {
                  const isConfirmed = booking.status === 'confirmed' || booking.status === 'upcoming';
                  return (
                    <div
                      key={booking.bookingId}
                      className="p-4 glass-card rounded-2xl space-y-3 hover:border-[#5D9253]/50 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-[#F1F6F2]">{booking.userName || 'Student'}</span>
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                                isConfirmed
                                  ? 'bg-[#5D9253]/20 text-[#84CC78] border-[#5D9253]/40'
                                  : booking.status === 'completed'
                                  ? 'bg-[#FFCB3D]/15 text-[#FFCB3D] border-[#FFCB3D]/30'
                                  : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                              }`}
                            >
                              {booking.status}
                            </span>
                          </div>
                          <span className="text-[10px] text-[#8BA190] font-mono">{booking.bookingId}</span>
                        </div>

                        <div className="flex items-center gap-2">
                          {booking.meetingLink && isConfirmed && (
                            <a
                              href={booking.meetingLink}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#5D9253] hover:bg-[#5D9253]/90 text-[#090E0A] text-[11px] font-bold rounded-xl transition shadow-sm"
                            >
                              <Video className="w-3.5 h-3.5" />
                              <span>Join Call</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}

                          <button
                            onClick={() => handleViewStudentContext(booking.bookingId)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#142017] hover:bg-[#1C2F20] text-[#D0DDD2] text-[11px] font-medium rounded-xl border border-[#557945]/30 transition"
                          >
                            <FileText className="w-3 h-3 text-[#5D9253]" />
                            <span>Context</span>
                          </button>
                        </div>
                      </div>

                      <div className="text-xs text-[#D0DDD2] bg-[#0E1610]/60 p-2.5 rounded-xl border border-[#557945]/20">
                        {booking.topic}
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#557945]/20 text-[11px] text-[#A2B5A6]">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3 text-[#FFCB3D]" />
                            {new Date(booking.slotStart).toUTCString()}
                          </span>
                          <span>&bull;</span>
                          <span>{booking.durationMinutes} min</span>
                        </div>

                        {isConfirmed && (
                          <div className="flex items-center gap-1.5">
                            <button
                              onClick={() => handleUpdateStatus(booking.bookingId, 'completed')}
                              disabled={updatingBookingId === booking.bookingId}
                              className="px-2.5 py-1 bg-[#142017] hover:bg-[#557945]/40 text-[#84CC78] hover:text-[#FFCB3D] border border-[#557945]/30 rounded-lg text-[10px] font-bold transition disabled:opacity-50"
                            >
                              {updatingBookingId === booking.bookingId ? '...' : 'Mark Completed'}
                            </button>
                            <button
                              onClick={() => handleUpdateStatus(booking.bookingId, 'cancelled')}
                              disabled={updatingBookingId === booking.bookingId}
                              className="px-2.5 py-1 bg-[#142017] hover:bg-rose-500/20 text-[#A2B5A6] hover:text-rose-400 border border-[#557945]/30 rounded-lg text-[10px] font-medium transition disabled:opacity-50"
                            >
                              Cancel Call
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Student Context Panel */}
          <div className="glass-panel rounded-2xl p-5 shadow-xl space-y-3">
            <h3 className="text-xs font-bold text-[#F1F6F2] uppercase tracking-wider">
              Student Context
            </h3>

            {loadingContext && (
              <div className="text-center py-10 text-xs text-[#8BA190] animate-pulse">
                Loading context...
              </div>
            )}

            {!loadingContext && !selectedContext && (
              <div className="text-center py-12 text-[#8BA190] text-xs">
                Select a session on the left to inspect student details.
              </div>
            )}

            {!loadingContext && selectedContext && (
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-[#0E1610] rounded-xl border border-[#557945]/30 space-y-1">
                  <div className="font-bold text-sm text-[#F1F6F2]">{selectedContext.studentName}</div>
                  <div className="text-[11px] text-[#A2B5A6]">{selectedContext.studentEmail}</div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between py-1 border-b border-[#557945]/20">
                    <span className="text-[#8BA190]">Domain</span>
                    <span className="font-semibold text-[#F1F6F2]">{selectedContext.targetDomain || 'General'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#557945]/20">
                    <span className="text-[#8BA190]">Education</span>
                    <span className="font-semibold text-[#F1F6F2]">{selectedContext.educationLevel || 'Undergraduate'}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-[#557945]/20">
                    <span className="text-[#8BA190]">Booking ID</span>
                    <span className="font-mono text-[10px] text-[#FFCB3D]">{selectedContext.bookingId}</span>
                  </div>
                </div>

                {selectedContext.recentNotes && (
                  <div className="p-3 bg-[#0E1610] rounded-xl border border-[#557945]/30">
                    <span className="text-[10px] font-bold text-[#FFCB3D] uppercase block mb-1">
                      Notes
                    </span>
                    <p className="text-[11px] text-[#D0DDD2]">{selectedContext.recentNotes}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Profile Settings with Editable Email */}
      {activeTab === 'profile' && (
        <div className="max-w-xl mx-auto glass-panel rounded-2xl p-6 shadow-xl border border-[#557945]/30">
          <h2 className="text-base font-bold text-[#F1F6F2] mb-1">Profile &amp; Email Settings</h2>
          <p className="text-xs text-[#A2B5A6] mb-6">
            Set your active email address to receive meeting notifications directly
          </p>

          {profileSaved && (
            <div className="mb-4 p-3 bg-[#5D9253]/15 border border-[#5D9253]/35 text-[#84CC78] text-xs rounded-xl font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#5D9253]" />
              <span>Profile updated successfully</span>
            </div>
          )}

          {profileError && (
            <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs rounded-xl">
              {profileError}
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-[#FFCB3D]" />
                <span>Mentor Email Address (for meeting invitations)</span>
              </label>
              <input
                type="email"
                required
                value={mentorProfile.email}
                onChange={(e) => setMentorProfile({ ...mentorProfile, email: e.target.value })}
                placeholder="you@domain.com"
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Company</label>
              <input
                type="text"
                value={mentorProfile.company}
                onChange={(e) => setMentorProfile({ ...mentorProfile, company: e.target.value })}
                placeholder="e.g. OpenAI, Stripe"
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Job Title</label>
              <input
                type="text"
                value={mentorProfile.role}
                onChange={(e) => setMentorProfile({ ...mentorProfile, role: e.target.value })}
                placeholder="e.g. Staff Engineer, Product Lead"
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Domain</label>
              <input
                type="text"
                value={mentorProfile.domain}
                onChange={(e) => setMentorProfile({ ...mentorProfile, domain: e.target.value })}
                placeholder="e.g. Artificial Intelligence"
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">City</label>
                <input
                  type="text"
                  value={mentorProfile.city}
                  onChange={(e) => setMentorProfile({ ...mentorProfile, city: e.target.value })}
                  placeholder="e.g. Bengaluru"
                  className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Seniority</label>
                <select
                  value={mentorProfile.seniority}
                  onChange={(e) => setMentorProfile({ ...mentorProfile, seniority: e.target.value })}
                  className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
                >
                  <option value="Senior" className="bg-[#0E1610]">Senior</option>
                  <option value="Lead" className="bg-[#0E1610]">Lead</option>
                  <option value="Principal" className="bg-[#0E1610]">Principal</option>
                  <option value="Director" className="bg-[#0E1610]">Director</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={profileSaving}
              className="w-full mt-2 py-2.5 px-4 rounded-xl text-xs font-bold text-[#090E0A] bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] hover:brightness-105 shadow-md shadow-[#FFCB3D]/15 transition disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
            >
              <Save className="w-4 h-4 text-[#090E0A]" />
              <span>{profileSaving ? 'Saving...' : 'Save Changes'}</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

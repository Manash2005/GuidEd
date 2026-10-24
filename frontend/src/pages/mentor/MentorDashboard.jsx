import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { mentorApi } from '../../services/api';
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
  Mail,
  Building2,
  MapPin,
  Award,
  AlertCircle
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

  const currentMentorId = dashboardData?.mentorId || user?.mentorId || 'MENTOR';

  // Chronological sort: upcoming first, then recent
  const sortedBookings = [...bookings].sort(
    (a, b) => new Date(a.slotStart) - new Date(b.slotStart)
  );

  return (
    <div className="space-y-6 font-sans">
      {/* Mentor Header & KPI Metrics */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E4E7EC]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-[#202124] tracking-tight">Mentor Workspace</h1>
            <span className="text-xs bg-[#EFF4FA] text-[#315E9E] border border-[#D0DCEB] px-2.5 py-0.5 rounded-full font-mono font-bold">
              ID: {currentMentorId}
            </span>
          </div>
          <p className="text-xs text-[#667085] mt-0.5">
            Manage your consultation sessions and prepare student career notes
          </p>
        </div>

        {/* Verifiable Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white border border-[#E4E7EC] px-4 py-2.5 rounded-xl shadow-xs">
            <span className="text-[11px] text-[#667085] font-semibold uppercase block">Upcoming</span>
            <span className="text-lg font-bold text-[#315E9E]">
              {dashboardData?.stats?.upcomingSessions || 0}
            </span>
          </div>
          <div className="bg-white border border-[#E4E7EC] px-4 py-2.5 rounded-xl shadow-xs">
            <span className="text-[11px] text-[#667085] font-semibold uppercase block">Completed</span>
            <span className="text-lg font-bold text-[#12B76A]">
              {dashboardData?.stats?.completedSessions || 0}
            </span>
          </div>
          <div className="bg-white border border-[#E4E7EC] px-4 py-2.5 rounded-xl shadow-xs">
            <span className="text-[11px] text-[#667085] font-semibold uppercase block">Total</span>
            <span className="text-lg font-bold text-[#202124]">{bookings.length}</span>
          </div>
        </div>
      </div>

      {statusFeedback && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-[#027A48] text-xs rounded-lg font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-[#12B76A]" />
          <span>{statusFeedback}</span>
        </div>
      )}


      {/* Tab 1: Sessions List & Student Preparation Context */}
      {activeTab === 'sessions' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-xs space-y-4">
            <h2 className="text-sm font-bold text-[#202124] uppercase tracking-wider">
              Chronological Consultations
            </h2>

            {sortedBookings.length === 0 ? (
              <div className="text-center py-12 text-[#667085] text-xs border border-dashed border-[#E4E7EC] rounded-xl p-6">
                No bookings scheduled yet for {currentMentorId}.
              </div>
            ) : (
              <div className="space-y-3">
                {sortedBookings.map((booking) => {
                  const isConfirmed = booking.status === 'confirmed' || booking.status === 'upcoming';
                  const isCompleted = booking.status === 'completed';
                  const isCancelled = booking.status === 'cancelled';

                  return (
                    <div
                      key={booking.bookingId}
                      className="p-4 bg-white rounded-xl border border-[#E4E7EC] shadow-xs space-y-3 hover:border-[#315E9E]/40 transition"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-[#202124]">
                              {booking.userName || 'Student'}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                                booking.status === 'pending'
                                  ? 'bg-amber-50 text-[#B54708] border-amber-200'
                                  : isConfirmed
                                  ? 'bg-emerald-50 text-[#027A48] border-emerald-200'
                                  : isCompleted
                                  ? 'bg-gray-100 text-[#344054] border-gray-200'
                                  : 'bg-rose-50 text-[#D92D20] border-rose-200'
                              }`}
                            >
                              {booking.status === 'pending' ? 'Pending Approval' : booking.status}
                            </span>
                          </div>
                          <span className="text-[11px] text-[#98A2B3] font-mono">
                            {booking.bookingId} &bull; {booking.userEmail}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {booking.meetingLink && isConfirmed && (
                            <a
                              href={booking.meetingLink}
                              target="_blank"
                              rel="noreferrer"
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#315E9E] hover:bg-[#26497B] text-white text-xs font-semibold rounded-lg transition shadow-xs"
                            >
                              <Video className="w-3.5 h-3.5" />
                              <span>Join Meet</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          )}

                          <button
                            onClick={() => handleViewStudentContext(booking.bookingId)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[#F8F9FA] text-[#344054] text-xs font-medium rounded-lg border border-[#D0D5DD] transition cursor-pointer"
                          >
                            <FileText className="w-3.5 h-3.5 text-[#667085]" />
                            <span>Student Context</span>
                          </button>
                        </div>
                      </div>

                      <div className="text-xs text-[#344054] space-y-1 bg-[#F8F9FA] p-3 rounded-lg">
                        <div className="flex items-center gap-2 text-[#202124] font-medium">
                          <Clock className="w-3.5 h-3.5 text-[#315E9E]" />
                          <span>
                            {new Date(booking.slotStart).toLocaleString()} (UTC) &bull;{' '}
                            {booking.durationMinutes || 30} mins
                          </span>
                        </div>
                        <div className="text-[#667085]">
                          <span className="font-semibold text-[#344054]">Topic: </span>
                          {booking.topic || 'Mentorship consultation'}
                        </div>
                      </div>

                      {/* Status Lifecycle Controls */}
                      <div className="pt-2 flex items-center justify-between text-xs">
                        <span className="text-[11px] text-[#98A2B3]">Update Stage:</span>
                        <div className="flex items-center gap-1.5">
                          {isConfirmed && (
                            <button
                              onClick={() => handleUpdateStatus(booking.bookingId, 'completed')}
                              disabled={updatingBookingId === booking.bookingId}
                              className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-[#027A48] border border-emerald-200 rounded-md text-[11px] font-semibold transition cursor-pointer"
                            >
                              Mark Completed
                            </button>
                          )}
                          {!isCancelled && (
                            <button
                              onClick={() => handleUpdateStatus(booking.bookingId, 'cancelled')}
                              disabled={updatingBookingId === booking.bookingId}
                              className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-[#D92D20] border border-rose-200 rounded-md text-[11px] font-semibold transition cursor-pointer"
                            >
                              Cancel Session
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Authorized Student Preparation Context Drawer */}
          <div className="bg-white rounded-xl border border-[#E4E7EC] p-5 shadow-xs space-y-4">
            <h3 className="text-sm font-bold text-[#202124] uppercase tracking-wider">
              Student Preparation Context
            </h3>

            {loadingContext ? (
              <div className="py-8 text-center text-xs text-[#667085] animate-pulse">
                Loading authorized student context...
              </div>
            ) : selectedContext ? (
              <div className="space-y-4 text-xs">
                <div className="p-3 bg-[#EFF4FA] border border-[#D0DCEB] rounded-lg space-y-1">
                  <div className="font-bold text-sm text-[#202124]">
                    {selectedContext.studentName || selectedContext.userName}
                  </div>
                  <div className="text-[#667085]">{selectedContext.studentEmail || selectedContext.userEmail}</div>
                  <div className="text-[#315E9E] font-medium pt-1">
                    Topic: {selectedContext.topic || 'General Mentorship'}
                  </div>
                </div>

                {selectedContext.studentProfile && (
                  <div className="space-y-1 bg-[#F8F9FA] p-3 rounded-lg">
                    <span className="font-semibold text-[#344054] block">Student Goals:</span>
                    <div>
                      Target Domain: <strong>{selectedContext.studentProfile.targetDomain || 'N/A'}</strong>
                    </div>
                    <div>
                      Education: <strong>{selectedContext.studentProfile.educationLevel || 'N/A'}</strong>
                    </div>
                  </div>
                )}

                {selectedContext.sharedNotes && (
                  <div className="p-3 bg-white border border-[#E4E7EC] rounded-lg space-y-1">
                    <span className="font-semibold text-[#344054] block">Student Questions:</span>
                    <p className="text-[#667085] leading-relaxed whitespace-pre-line">
                      {selectedContext.sharedNotes}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-12 text-center text-[#98A2B3] text-xs">
                Click <span className="font-semibold text-[#344054]">"Student Context"</span> on any session to view authorized preparation notes.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Profile Settings with Editable Email */}
      {activeTab === 'profile' && (
        <div className="max-w-xl mx-auto bg-white rounded-xl p-6 shadow-xs border border-[#E4E7EC]">
          <h2 className="text-base font-bold text-[#202124] mb-1">Profile &amp; Email Settings</h2>
          <p className="text-xs text-[#667085] mb-6">
            Configure your active email address to receive meeting notifications directly.
          </p>

          {profileSaved && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-[#027A48] text-xs rounded-lg font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#12B76A]" />
              <span>Profile updated successfully</span>
            </div>
          )}

          {profileError && (
            <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-[#D92D20] text-xs rounded-lg">
              {profileError}
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-[#315E9E]" />
                <span>Mentor Email Address (for meeting invitations)</span>
              </label>
              <input
                type="email"
                required
                value={mentorProfile.email}
                onChange={(e) => setMentorProfile({ ...mentorProfile, email: e.target.value })}
                placeholder="you@domain.com"
                className="w-full px-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Company</label>
              <input
                type="text"
                value={mentorProfile.company}
                onChange={(e) => setMentorProfile({ ...mentorProfile, company: e.target.value })}
                placeholder="e.g. OpenAI, Stripe"
                className="w-full px-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Job Title</label>
              <input
                type="text"
                value={mentorProfile.role}
                onChange={(e) => setMentorProfile({ ...mentorProfile, role: e.target.value })}
                placeholder="e.g. Staff Engineer, Product Lead"
                className="w-full px-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Domain</label>
              <input
                type="text"
                value={mentorProfile.domain}
                onChange={(e) => setMentorProfile({ ...mentorProfile, domain: e.target.value })}
                placeholder="e.g. Artificial Intelligence"
                className="w-full px-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#344054] mb-1.5">City</label>
                <input
                  type="text"
                  value={mentorProfile.city}
                  onChange={(e) => setMentorProfile({ ...mentorProfile, city: e.target.value })}
                  placeholder="e.g. Bengaluru"
                  className="w-full px-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#344054] mb-1.5">Seniority</label>
                <select
                  value={mentorProfile.seniority}
                  onChange={(e) => setMentorProfile({ ...mentorProfile, seniority: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
                >
                  <option value="Senior">Senior</option>
                  <option value="Lead">Lead</option>
                  <option value="Principal">Principal</option>
                  <option value="Director">Director</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={profileSaving}
              className="w-full mt-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-[#315E9E] hover:bg-[#26497B] transition disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer shadow-xs"
            >
              <Save className="w-4 h-4 text-white" />
              <span>{profileSaving ? 'Saving...' : 'Save Profile Changes'}</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

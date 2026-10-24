import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { studentApi, authApi } from '../../services/api';
import {
  MessageSquare,
  Calendar,
  User,
  Send,
  Video,
  Clock,
  Sparkles,
  ExternalLink,
  Check,
  X,
  Mail,
  CheckCircle2,
  Plus,
  RotateCcw
} from 'lucide-react';

export default function StudentDashboard() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'chat';

  const [dashboardData, setDashboardData] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Booking Modal State
  const [bookingModalMentor, setBookingModalMentor] = useState(null);
  const [bookingDate, setBookingDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split('T')[0];
  });
  const [rawSlots, setRawSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [bookingTopic, setBookingTopic] = useState('');
  const [isBooking, setIsBooking] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState(null);

  // Profile Edit State (with editable email)
  const [email, setEmail] = useState(user?.email || '');
  const [fullName, setFullName] = useState(user?.fullName || '');
  const [targetDomain, setTargetDomain] = useState(user?.targetDomain || 'Artificial Intelligence');
  const [educationLevel, setEducationLevel] = useState(user?.educationLevel || 'Undergraduate');
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState('');

  useEffect(() => {
    loadDashboard();
    loadBookings();
    loadConversations();
  }, [user]);

  useEffect(() => {
    if (activeConvId) {
      loadActiveConversationMessages(activeConvId);
    }
  }, [activeConvId]);

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, isSending]);

  const loadDashboard = async () => {
    try {
      const data = await studentApi.getDashboard();
      setDashboardData(data);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
  };

  const loadBookings = async () => {
    try {
      const data = await studentApi.getBookings();
      setBookings(data || []);
    } catch (err) {
      console.error('Failed to load bookings:', err);
    }
  };

  const loadConversations = async () => {
    try {
      const data = await studentApi.getConversations();
      setConversations(data || []);
      if (data && data.length > 0 && !activeConvId) {
        setActiveConvId(data[0].conversationId);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const loadActiveConversationMessages = async (convId) => {
    if (!convId) {
      setChatMessages([]);
      return;
    }
    try {
      const detail = await studentApi.getConversation(convId);
      if (detail && detail.messages) {
        setChatMessages(detail.messages);
      }
    } catch (err) {
      console.error('Failed to load conversation messages:', err);
    }
  };

  const handleNewChat = () => {
    setActiveConvId(null);
    setChatMessages([]);
    setErrorMsg('');
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || isSending) return;

    setErrorMsg('');
    const userText = inputQuery.trim();
    setInputQuery('');
    setIsSending(true);

    const tempUserMsg = {
      messageId: `temp_${Date.now()}`,
      role: 'user',
      content: userText
    };
    setChatMessages((prev) => [...prev, tempUserMsg]);

    try {
      if (!activeConvId) {
        // Create new conversation with the initial query
        const newConv = await studentApi.createConversation({
          initialMessage: userText
        });
        setActiveConvId(newConv.conversationId);
        if (newConv.messages && newConv.messages.length > 0) {
          setChatMessages(newConv.messages);
        }
        await loadConversations();
      } else {
        // Send to existing conversation and retrieve LLM recommendations
        const asstMsg = await studentApi.sendMessage(activeConvId, userText);
        setChatMessages((prev) => {
          const filtered = prev.filter((m) => m.messageId !== tempUserMsg.messageId);
          return [...filtered, tempUserMsg, asstMsg];
        });
        await loadConversations();
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to process AI recommendation');
    } finally {
      setIsSending(false);
    }
  };

  // Open booking modal for an LLM-suggested mentor
  const handleOpenBooking = async (mentor) => {
    setBookingModalMentor(mentor);
    setBookingTopic(`Career mentorship in ${mentor.domain || 'Technology'}`);
    setSelectedSlot(null);
    setBookingSuccess(null);
    fetchSlotsForDate(mentor.mentorId, bookingDate);
  };

  const fetchSlotsForDate = async (mentorId, date) => {
    setLoadingSlots(true);
    setRawSlots([]);
    try {
      const res = await studentApi.getMentorSlots(mentorId, date, 30);
      // Backend returns array of { slotStart, slotEnd, isAvailable }
      const slotsList = Array.isArray(res) ? res : (res.availableSlots || []);
      setRawSlots(slotsList);
    } catch (err) {
      console.error('Failed to fetch mentor slots:', err);
    } finally {
      setLoadingSlots(false);
    }
  };

  const formatSlotTime = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC';
  };

  const handleConfirmBooking = async () => {
    if (!selectedSlot || !bookingModalMentor) return;

    setIsBooking(true);
    setErrorMsg('');
    try {
      const payload = {
        mentorId: bookingModalMentor.mentorId,
        slotStart: selectedSlot.slotStart || selectedSlot.start,
        durationMinutes: 30,
        topic: bookingTopic.trim() || 'Mentorship Discussion'
      };
      const res = await studentApi.bookSlot(payload);
      setBookingSuccess(res);
      loadBookings();
      loadDashboard();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to complete booking');
    } finally {
      setIsBooking(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Cancel this scheduled mentorship session?')) return;
    try {
      await studentApi.cancelBooking(bookingId);
      loadBookings();
      loadDashboard();
    } catch (err) {
      alert(err.message || 'Failed to cancel session');
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setProfileError('');
    try {
      await authApi.updateProfile({
        email: email.trim().toLowerCase(),
        fullName: fullName.trim(),
        targetDomain,
        educationLevel
      });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err) {
      setProfileError(err.message || 'Failed to update profile');
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* Clean Header & Stats */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#557945]/20">
        <div>
          <h1 className="text-2xl font-extrabold text-[#F1F6F2] tracking-tight">Student Workspace</h1>
        </div>

        {/* Real Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="glass-card px-4 py-2 rounded-2xl">
            <span className="text-[10px] text-[#8BA190] font-semibold uppercase block">Upcoming</span>
            <span className="text-base font-bold text-[#84CC78]">{dashboardData?.stats?.upcomingBookings || 0}</span>
          </div>
          <div className="glass-card px-4 py-2 rounded-2xl">
            <span className="text-[10px] text-[#8BA190] font-semibold uppercase block">Completed</span>
            <span className="text-base font-bold text-[#FFCB3D]">{dashboardData?.stats?.completedBookings || 0}</span>
          </div>
        </div>
      </div>

      {/* Tabs - strictly AI Advisor, My Bookings, Profile (NO mentor directory) */}
      <div className="flex items-center gap-2 border-b border-[#557945]/20 pb-2">
        <button
          onClick={() => setSearchParams({ tab: 'chat' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'chat'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-[#FFCB3D]" />
          <span>AI Career Advisor</span>
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
          <span>My Bookings ({bookings.length})</span>
        </button>

        <button
          onClick={() => setSearchParams({ tab: 'profile' })}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition ${
            activeTab === 'profile'
              ? 'bg-[#557945]/30 text-[#FFCB3D] border border-[#557945]/40 shadow-sm'
              : 'text-[#A2B5A6] hover:text-[#F1F6F2] hover:bg-[#152318]'
          }`}
        >
          <User className="w-3.5 h-3.5 text-[#84CC78]" />
          <span>Profile &amp; Email</span>
        </button>
      </div>

      {/* Tab 1: AI Chat & LLM Mentor Suggestions (Full clean layout without pre-query mentor list) */}
      {activeTab === 'chat' && (
        <div className="glass-panel rounded-3xl flex flex-col h-[750px] shadow-2xl overflow-hidden border border-[#557945]/35 max-w-5xl mx-auto">
          {/* Header */}
          <div className="px-6 py-4 border-b border-[#557945]/25 bg-[#0E1610]/90 flex flex-col sm:flex-row sm:items-center justify-between gap-3 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-[#84CC78] shadow-sm animate-pulse" />
              <div>
                <h2 className="text-base sm:text-lg font-bold text-[#F1F6F2] tracking-tight">AI Career &amp; Mentor Matching</h2>
                <p className="text-xs text-[#8BA190]">Personalized guidance grounded in verified mentor experience</p>
              </div>
            </div>

            <div className="flex items-center gap-2.5">
              {conversations.length > 1 && (
                <select
                  value={activeConvId || ''}
                  onChange={(e) => setActiveConvId(e.target.value)}
                  className="glass-input text-xs sm:text-sm px-3 py-1.5 rounded-xl border border-[#557945]/35 text-[#F1F6F2] bg-[#0E1610] focus:outline-none"
                >
                  {conversations.map((c) => (
                    <option key={c.conversationId} value={c.conversationId} className="bg-[#0E1610]">
                      {c.title ? (c.title.length > 28 ? c.title.slice(0, 28) + '...' : c.title) : 'Career Session'}
                    </option>
                  ))}
                </select>
              )}

              <button
                onClick={handleNewChat}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-[#142017] hover:bg-[#1C2F20] text-[#FFCB3D] border border-[#557945]/40 text-xs sm:text-sm font-semibold transition shadow-sm cursor-pointer"
                title="Start a new career advising session"
              >
                <Plus className="w-4 h-4" />
                <span>New Session</span>
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 p-6 sm:p-8 overflow-y-auto space-y-6">
            {chatMessages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#A2B5A6]">
                <div className="w-14 h-14 rounded-3xl bg-[#142017] border border-[#557945]/40 flex items-center justify-center text-[#FFCB3D] mb-4 shadow-lg">
                  <Sparkles className="w-7 h-7" />
                </div>
                <h3 className="text-lg sm:text-xl font-bold text-[#F1F6F2] mb-2">How can our mentors help you today?</h3>
                <p className="text-sm sm:text-base max-w-lg mb-8 text-[#8BA190] leading-relaxed">
                  Describe your career goals, industry pivot, or technical challenges. The AI matching engine analyzes verified mentor profiles and presents the top 2–3 best-suited mentors for you to select and book a 1:1 consultation.
                </p>
                <div className="flex flex-wrap gap-3 justify-center max-w-xl">
                  <button
                    onClick={() => setInputQuery('I want a senior AI architect to guide me in machine learning and LLM applications.')}
                    className="text-sm sm:text-base bg-[#142017] hover:bg-[#1C2F20] text-[#D0DDD2] hover:text-[#FFCB3D] px-4 py-2.5 rounded-2xl border border-[#557945]/30 transition shadow-sm"
                  >
                    AI Architecture &amp; LLMs &rarr;
                  </button>
                  <button
                    onClick={() => setInputQuery('Looking for guidance from an experienced founder on seed fundraising.')}
                    className="text-sm sm:text-base bg-[#142017] hover:bg-[#1C2F20] text-[#D0DDD2] hover:text-[#FFCB3D] px-4 py-2.5 rounded-2xl border border-[#557945]/30 transition shadow-sm"
                  >
                    Seed Fundraising &rarr;
                  </button>
                  <button
                    onClick={() => setInputQuery('Looking for a product management mentor experienced in AI SaaS products.')}
                    className="text-sm sm:text-base bg-[#142017] hover:bg-[#1C2F20] text-[#D0DDD2] hover:text-[#FFCB3D] px-4 py-2.5 rounded-2xl border border-[#557945]/30 transition shadow-sm"
                  >
                    AI Product Management &rarr;
                  </button>
                </div>
              </div>
            )}

            {chatMessages.map((msg) => (
              <div
                key={msg.messageId}
                className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`rounded-3xl p-5 sm:p-6 text-base sm:text-[17px] leading-relaxed shadow-lg ${
                    msg.role === 'user'
                      ? 'max-w-[85%] rounded-br-md bg-gradient-to-r from-[#213824] to-[#2E4F32] text-[#F1F6F2] border border-[#557945]/50'
                      : 'max-w-[92%] sm:max-w-[88%] rounded-bl-md glass-panel-elevated text-[#F1F6F2] border border-[#557945]/35 space-y-5'
                  }`}
                >
                  <p className="text-base sm:text-[17px] text-[#F1F6F2] font-normal leading-relaxed">{msg.content}</p>

                  {/* LLM Suggested Mentors (2-3 Structured Results) */}
                  {msg.recommendations && msg.recommendations.length > 0 && (
                    <div className="mt-6 space-y-5 pt-5 border-t border-[#557945]/30">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-[#FFCB3D] uppercase tracking-wider flex items-center gap-2">
                          <Sparkles className="w-4 h-4 text-[#FFCB3D]" />
                          Top Mentor Matches ({msg.recommendations.length} Options)
                        </span>
                        <span className="text-xs sm:text-sm text-[#8BA190]">Compare and select a mentor below</span>
                      </div>

                      <div className="space-y-5">
                        {msg.recommendations.map((rec) => {
                          const matchPct = rec.matchPercentage ?? (rec.compositeScore ? Math.round(rec.compositeScore * 100) : 88);
                          return (
                            <div
                              key={rec.mentorId}
                              className="p-5 sm:p-6 bg-[#0B130D]/95 border border-[#557945]/40 rounded-3xl space-y-4 hover:border-[#FFCB3D]/60 transition-all duration-200 shadow-xl"
                            >
                              {/* Teacher Profile Header */}
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                <div className="flex items-center gap-4">
                                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#1C2F20] to-[#2E4F32] border border-[#557945]/60 flex items-center justify-center text-xl font-extrabold text-[#FFCB3D] shadow-inner shrink-0">
                                    {rec.name?.charAt(0) || 'M'}
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2.5">
                                      <h4 className="font-extrabold text-[#F1F6F2] text-lg sm:text-xl tracking-tight">
                                        {rec.name}
                                      </h4>
                                      <span className="text-xs font-mono font-bold text-[#8BA190] bg-[#142017] px-2.5 py-1 rounded-lg border border-[#557945]/30">
                                        {rec.mentorId}
                                      </span>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2 text-sm text-[#A2B5A6] mt-1">
                                      <span className="text-[#84CC78] font-bold">{rec.seniority || 'Senior Specialist'}</span>
                                      <span>•</span>
                                      <span className="text-[#F1F6F2] font-semibold">{rec.company || 'Tech Leader'}</span>
                                      <span>•</span>
                                      <span className="text-[#8BA190]">{rec.city || 'Global'}</span>
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2 self-start sm:self-auto">
                                  <span className="text-sm sm:text-base font-mono font-bold bg-[#5D9253]/25 text-[#84CC78] border border-[#5D9253]/50 px-4 py-1.5 rounded-full shadow-sm flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-[#84CC78] animate-pulse" />
                                    {matchPct}% Match
                                  </span>
                                </div>
                              </div>

                              {/* Domain & Sectors */}
                              <div className="flex flex-wrap items-center gap-2 pt-1">
                                <span className="px-3.5 py-1.5 rounded-xl bg-[#FFCB3D]/15 text-[#FFCB3D] border border-[#FFCB3D]/35 text-xs sm:text-sm font-bold">
                                  {rec.domain}
                                </span>
                                {Array.isArray(rec.sectorsOfExpertise) && rec.sectorsOfExpertise.slice(0, 3).map((sec, i) => (
                                  <span key={i} className="px-3.5 py-1.5 rounded-xl bg-[#142017] text-[#D0DDD2] border border-[#557945]/30 text-xs sm:text-sm font-medium">
                                    {sec}
                                  </span>
                                ))}
                              </div>

                              {/* Match Reason */}
                              <div className="p-4 sm:p-5 bg-[#080D09]/80 rounded-2xl border border-[#557945]/25 space-y-2.5">
                                <div className="text-xs sm:text-sm font-bold text-[#84CC78] uppercase tracking-wider">
                                  Why Matched For You
                                </div>
                                <p className="text-sm sm:text-base text-[#F1F6F2] leading-relaxed font-normal">
                                  {rec.matchReason}
                                </p>
                                {rec.relevantExperience && (
                                  <p className="text-sm text-[#D0DDD2] pt-2.5 border-t border-[#557945]/20 leading-relaxed">
                                    <span className="font-semibold text-[#A2B5A6]">Verified Background: </span>
                                    {rec.relevantExperience}
                                  </p>
                                )}
                              </div>

                              {/* Action CTA */}
                              <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-[#557945]/25">
                                <span className="text-xs sm:text-sm text-[#8BA190]">
                                  Google Calendar session + Meet invitation created upon slot selection
                                </span>
                                <button
                                  onClick={() => handleOpenBooking(rec)}
                                  className="flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] text-[#090E0A] text-sm sm:text-base font-bold transition hover:brightness-105 shadow-md cursor-pointer ml-auto"
                                >
                                  <Calendar className="w-4 h-4 text-[#090E0A]" />
                                  <span>Select Mentor &amp; Book</span>
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* In-Flight Matching Indicator */}
            {isSending && (
              <div className="flex items-start gap-3 animate-in fade-in duration-200">
                <div className="w-12 h-12 rounded-2xl bg-[#142017] border border-[#557945]/40 flex items-center justify-center text-[#FFCB3D] shadow-sm animate-pulse">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div className="glass-panel-elevated px-5 py-4 rounded-3xl rounded-bl-sm border border-[#557945]/35 text-sm sm:text-base text-[#84CC78] flex items-center gap-2.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#84CC78] animate-ping" />
                  <span>Analyzing candidate mentor profiles &amp; calculating match alignment...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {errorMsg && (
            <div className="px-6 py-3 bg-rose-500/10 border-t border-rose-500/20 text-rose-300 text-sm">
              {errorMsg}
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={handleSendMessage} className="p-4 sm:p-5 bg-[#0E1610]/95 border-t border-[#557945]/30 flex gap-3.5 items-center backdrop-blur-md">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Describe your career goal or ask for a specific mentor specialization..."
              className="flex-1 glass-input rounded-2xl px-5 py-4 text-base sm:text-[17px] text-[#F1F6F2] placeholder-[#557945] focus:outline-none"
            />
            <button
              type="submit"
              disabled={isSending || !inputQuery.trim()}
              className="px-6 sm:px-7 py-4 bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] hover:brightness-105 disabled:opacity-40 text-[#090E0A] rounded-2xl text-sm sm:text-base font-bold flex items-center gap-2 transition shadow-lg cursor-pointer shrink-0"
            >
              <span>{isSending ? 'Matching...' : 'Ask Advisor'}</span>
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      )}

      {/* Tab 2: Scheduled Bookings */}
      {activeTab === 'bookings' && (
        <div className="glass-panel rounded-2xl p-6 shadow-xl border border-[#557945]/30">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-bold text-[#F1F6F2]">My Scheduled Sessions</h2>
            <span className="text-xs font-mono font-bold text-[#FFCB3D] bg-[#0E1610] px-2.5 py-1 rounded-lg border border-[#557945]/30">
              {bookings.length} Bookings
            </span>
          </div>

          {bookings.length === 0 ? (
            <div className="text-center py-12 text-[#8BA190] text-xs border border-dashed border-[#557945]/30 rounded-2xl p-6">
              No sessions booked yet. Ask the AI advisor above to receive mentor recommendations.
            </div>
          ) : (
            <div className="space-y-3">
              {bookings.map((booking) => {
                const isUpcoming = booking.status === 'confirmed' || booking.status === 'upcoming';
                return (
                  <div
                    key={booking.bookingId}
                    className="p-4 glass-card rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-[#F1F6F2]">{booking.mentorName}</span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${
                            isUpcoming
                              ? 'bg-[#5D9253]/20 text-[#84CC78] border-[#5D9253]/40'
                              : booking.status === 'completed'
                              ? 'bg-[#FFCB3D]/15 text-[#FFCB3D] border-[#FFCB3D]/30'
                              : 'bg-rose-500/15 text-rose-300 border-rose-500/30'
                          }`}
                        >
                          {booking.status}
                        </span>
                      </div>
                      <p className="text-xs text-[#D0DDD2]">{booking.topic}</p>
                      <div className="flex items-center gap-3 text-[11px] text-[#A2B5A6]">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-[#FFCB3D]" />
                          {new Date(booking.slotStart).toUTCString()}
                        </span>
                        <span>&bull;</span>
                        <span>{booking.durationMinutes} min</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {booking.meetingLink && isUpcoming && (
                        <a
                          href={booking.meetingLink}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#5D9253] hover:bg-[#5D9253]/90 text-[#090E0A] text-xs font-bold rounded-xl transition shadow-sm"
                        >
                          <Video className="w-3.5 h-3.5" />
                          <span>Join Meet</span>
                          <ExternalLink className="w-3 h-3 ml-0.5" />
                        </a>
                      )}

                      {isUpcoming && (
                        <button
                          onClick={() => handleCancelBooking(booking.bookingId)}
                          className="px-3 py-1.5 bg-[#142017] hover:bg-rose-500/20 text-[#A2B5A6] hover:text-rose-400 border border-[#557945]/30 text-xs font-medium rounded-xl transition"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Profile Settings with Editable Email */}
      {activeTab === 'profile' && (
        <div className="max-w-xl mx-auto glass-panel rounded-2xl p-6 shadow-xl border border-[#557945]/30">
          <h2 className="text-base font-bold text-[#F1F6F2] mb-1">Profile &amp; Email Settings</h2>
          <p className="text-xs text-[#A2B5A6] mb-6">Update your email address to receive meeting confirmations</p>

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
                <span>Student Email Address (for meeting invitations)</span>
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@domain.com"
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Domain Interest</label>
              <select
                value={targetDomain}
                onChange={(e) => setTargetDomain(e.target.value)}
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              >
                <option value="Artificial Intelligence" className="bg-[#0E1610]">Artificial Intelligence</option>
                <option value="Product Management" className="bg-[#0E1610]">Product Management</option>
                <option value="Software Engineering" className="bg-[#0E1610]">Software Engineering</option>
                <option value="Data Science & Analytics" className="bg-[#0E1610]">Data Science & Analytics</option>
                <option value="Venture Capital & Startups" className="bg-[#0E1610]">Venture Capital & Startups</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Education Level</label>
              <select
                value={educationLevel}
                onChange={(e) => setEducationLevel(e.target.value)}
                className="w-full px-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
              >
                <option value="Undergraduate" className="bg-[#0E1610]">Undergraduate</option>
                <option value="Postgraduate" className="bg-[#0E1610]">Postgraduate</option>
                <option value="Early Professional" className="bg-[#0E1610]">Early Professional</option>
                <option value="Career Switcher" className="bg-[#0E1610]">Career Switcher</option>
              </select>
            </div>

            <button
              type="submit"
              className="w-full mt-2 py-2.5 px-4 rounded-xl text-xs font-bold text-[#090E0A] bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] hover:brightness-105 shadow-sm transition cursor-pointer"
            >
              Save Changes
            </button>
          </form>
        </div>
      )}

      {/* Booking Slot Modal: Clearly shows both Available and Booked Slots */}
      {bookingModalMentor && (
        <div className="fixed inset-0 z-50 bg-[#090E0A]/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-panel-elevated rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-[#557945]/40 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start justify-between pb-3 border-b border-[#557945]/25">
              <div>
                <span className="text-[10px] font-bold text-[#5D9253] uppercase block">
                  Book Session
                </span>
                <h3 className="text-base font-bold text-[#F1F6F2]">
                  {bookingModalMentor.name}
                </h3>
                <span className="text-xs text-[#A2B5A6]">{bookingModalMentor.domain}</span>
              </div>
              <button
                onClick={() => setBookingModalMentor(null)}
                className="text-[#8BA190] hover:text-[#F1F6F2] p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {bookingSuccess ? (
              <div className="py-6 text-center space-y-4">
                <div className="w-12 h-12 rounded-full bg-[#5D9253]/20 border border-[#5D9253]/40 flex items-center justify-center mx-auto">
                  <Check className="w-6 h-6 text-[#84CC78]" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-[#F1F6F2]">Session Booked</h4>
                  <p className="text-xs text-[#A2B5A6] mt-1">
                    Google Calendar event created. Notifications sent to both emails.
                  </p>
                </div>

                {bookingSuccess.meetingLink && (
                  <div className="p-3 bg-[#0E1610] rounded-xl border border-[#557945]/30">
                    <span className="text-[10px] text-[#8BA190] block mb-1">Meet Link:</span>
                    <a
                      href={bookingSuccess.meetingLink}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs font-mono text-[#FFCB3D] hover:underline break-all"
                    >
                      {bookingSuccess.meetingLink}
                    </a>
                  </div>
                )}

                <button
                  onClick={() => {
                    setBookingModalMentor(null);
                    setSearchParams({ tab: 'bookings' });
                  }}
                  className="px-4 py-2 bg-gradient-to-r from-[#FFCB3D] to-[#F1A344] text-[#090E0A] font-bold text-xs rounded-xl transition"
                >
                  View in My Bookings
                </button>
              </div>
            ) : (
              <div className="space-y-4 py-4 text-xs">
                <div>
                  <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Select Date</label>
                  <input
                    type="date"
                    value={bookingDate}
                    min={new Date().toISOString().split('T')[0]}
                    onChange={(e) => {
                      setBookingDate(e.target.value);
                      fetchSlotsForDate(bookingModalMentor.mentorId, e.target.value);
                    }}
                    className="w-full px-3.5 py-2 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Topic</label>
                  <input
                    type="text"
                    value={bookingTopic}
                    onChange={(e) => setBookingTopic(e.target.value)}
                    placeholder="Discussion topic"
                    className="w-full px-3.5 py-2 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-semibold text-[#D0DDD2]">Time Slots (30 min)</label>
                    <span className="text-[10px] text-[#8BA190]">Shows available and booked slots</span>
                  </div>

                  {loadingSlots ? (
                    <div className="text-center py-6 text-xs text-[#8BA190] animate-pulse">
                      Checking availability...
                    </div>
                  ) : rawSlots.length === 0 ? (
                    <div className="text-center py-6 text-xs text-[#8BA190] border border-dashed border-[#557945]/30 rounded-xl">
                      No slots found for this date.
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-1">
                      {rawSlots.map((slot, idx) => {
                        const isAvailable = slot.isAvailable !== false;
                        const startLabel = formatSlotTime(slot.slotStart || slot.start);
                        const isSelected = selectedSlot && (selectedSlot.slotStart === slot.slotStart || selectedSlot.start === slot.start);

                        if (!isAvailable) {
                          return (
                            <div
                              key={idx}
                              className="p-2 rounded-xl border border-rose-500/20 bg-rose-500/5 text-rose-300/60 text-[11px] font-mono flex items-center justify-between cursor-not-allowed opacity-60"
                              title="This slot is already booked"
                            >
                              <span>{startLabel}</span>
                              <span className="text-[9px] uppercase font-bold text-rose-400">Booked</span>
                            </div>
                          );
                        }

                        return (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => setSelectedSlot(slot)}
                            className={`p-2 rounded-xl border text-[11px] font-mono font-medium flex items-center justify-between transition ${
                              isSelected
                                ? 'bg-[#5D9253]/30 border-[#5D9253] text-[#FFCB3D] shadow-sm'
                                : 'bg-[#142017] border-[#557945]/30 text-[#D0DDD2] hover:bg-[#1C2F20]'
                            }`}
                          >
                            <span>{startLabel}</span>
                            <span className="text-[9px] uppercase font-bold text-[#84CC78]">Available</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-[#557945]/20 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setBookingModalMentor(null)}
                    className="px-4 py-2 bg-[#142017] text-[#A2B5A6] rounded-xl text-xs font-medium hover:text-[#F1F6F2]"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmBooking}
                    disabled={isBooking || !selectedSlot}
                    className="px-5 py-2 bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] text-[#090E0A] font-bold text-xs rounded-xl hover:brightness-105 disabled:opacity-40 transition shadow-sm"
                  >
                    {isBooking ? 'Booking...' : 'Confirm'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

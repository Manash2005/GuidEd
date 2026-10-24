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
  RotateCcw,
  Search,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Building2,
  MapPin,
  Award,
  Layers,
  Wrench,
  Info,
  CalendarCheck,
  Edit2,
  Trash2
} from 'lucide-react';

export default function StudentDashboard() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get('tab') || 'chat';

  // Navigation tab helper
  const setActiveTab = (tab) => {
    if (tab === 'chat') {
      setSearchParams({});
    } else {
      setSearchParams({ tab });
    }
  };

  const [dashboardData, setDashboardData] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeConvId, setActiveConvId] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  // Sidebar responsive toggle
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Rename conversation modal state
  const [renamingConvId, setRenamingConvId] = useState(null);
  const [newTitleInput, setNewTitleInput] = useState('');

  // Expandable mentor cards state
  const [expandedMentors, setExpandedMentors] = useState({});

  const toggleMentorExpand = (mentorId) => {
    setExpandedMentors((prev) => ({
      ...prev,
      [mentorId]: !prev[mentorId]
    }));
  };

  const messagesEndRef = useRef(null);
  const chatInputRef = useRef(null);

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
  const [bookingConflictError, setBookingConflictError] = useState('');

  // Profile Edit State
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
    if (window.innerWidth < 768) setSidebarOpen(false);
    setTimeout(() => chatInputRef.current?.focus(), 100);
  };

  const handleSelectConversation = (convId) => {
    setActiveConvId(convId);
    setErrorMsg('');
    if (window.innerWidth < 768) setSidebarOpen(false);
  };

  const handleStartRename = (conv, e) => {
    e.stopPropagation();
    setRenamingConvId(conv.conversationId);
    setNewTitleInput(conv.title || '');
  };

  const handleSaveRename = async (e) => {
    e.preventDefault();
    if (!renamingConvId || !newTitleInput.trim()) return;
    try {
      await studentApi.updateConversationTitle(renamingConvId, newTitleInput.trim());
      setConversations((prev) =>
        prev.map((c) =>
          c.conversationId === renamingConvId ? { ...c, title: newTitleInput.trim() } : c
        )
      );
      setRenamingConvId(null);
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  };

  const handleDeleteConversation = async (convId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this career conversation?')) return;
    try {
      await studentApi.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.conversationId !== convId));
      if (activeConvId === convId) {
        handleNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!inputQuery.trim() || isSending) return;

    setErrorMsg('');
    const userText = inputQuery.trim();
    setInputQuery('');
    setIsSending(true);

    const tempUserMsg = {
      messageId: `temp_${Date.now()}`,
      role: 'user',
      content: userText,
      recommendations: []
    };
    setChatMessages((prev) => [...prev, tempUserMsg]);

    try {
      if (!activeConvId) {
        // Create new conversation with auto-generated title
        const newConv = await studentApi.createConversation({
          initialMessage: userText
        });
        setActiveConvId(newConv.conversationId);
        if (newConv.messages && newConv.messages.length > 0) {
          setChatMessages(newConv.messages);
        }
        await loadConversations();
      } else {
        // Send message to current conversation
        const asstMsg = await studentApi.sendMessage(activeConvId, userText);
        setChatMessages((prev) => {
          const filtered = prev.filter((m) => m.messageId !== tempUserMsg.messageId);
          return [...filtered, tempUserMsg, asstMsg];
        });
        await loadConversations();
      }
    } catch (err) {
      // Auto-recovery: If network glitch or proxy dropped connection, check if backend saved the response in MongoDB
      try {
        if (activeConvId) {
          const detail = await studentApi.getConversation(activeConvId);
          if (detail && detail.messages && detail.messages.length > 0) {
            const lastMsg = detail.messages[detail.messages.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              setChatMessages(detail.messages);
              await loadConversations();
              return;
            }
          }
        }
      } catch (checkErr) {
        // Fall back to showing friendly error message
      }

      setErrorMsg(
        err.message ||
        'I can help with career planning, professional skills, interview preparation, and finding mentors. Could you rephrase your question around your career goals?'
      );
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
    setBookingConflictError('');
    fetchSlotsForDate(mentor.mentorId, bookingDate);
  };

  const fetchSlotsForDate = async (mentorId, dateStr) => {
    setLoadingSlots(true);
    setSelectedSlot(null);
    setBookingConflictError('');
    try {
      const slots = await studentApi.getMentorSlots(mentorId, dateStr, 30);
      setRawSlots(slots || []);
    } catch (err) {
      console.error('Failed to fetch mentor slots:', err);
      setRawSlots([]);
    } finally {
      setLoadingSlots(false);
    }
  };

  const handleDateChange = (e) => {
    const newDate = e.target.value;
    setBookingDate(newDate);
    if (bookingModalMentor) {
      fetchSlotsForDate(bookingModalMentor.mentorId, newDate);
    }
  };

  // Safe Single Slot Selection Fix (Phase 4)
  const handleSelectSlot = (slot) => {
    if (slot.isAvailable === false) return;
    // Strictly assign the selected slot object
    setSelectedSlot(slot);
    setBookingConflictError('');
  };

  const handleConfirmBooking = async () => {
    if (!selectedSlot || !bookingModalMentor) return;
    setIsBooking(true);
    setBookingConflictError('');

    try {
      const payload = {
        mentorId: bookingModalMentor.mentorId,
        slotStart: selectedSlot.slotStart,
        durationMinutes: 30,
        topic: bookingTopic.trim() || `Mentorship session with ${bookingModalMentor.name}`
      };

      const result = await studentApi.bookSlot(payload);
      setBookingSuccess(result);
      await loadBookings();
      await loadDashboard();
    } catch (err) {
      if (err.status === 409 || err.message?.includes('already has a confirmed booking')) {
        setBookingConflictError(
          'This slot was just booked by another user. Please choose a different available time slot.'
        );
        fetchSlotsForDate(bookingModalMentor.mentorId, bookingDate);
      } else {
        setBookingConflictError(err.message || 'Failed to complete booking. Please try again.');
      }
    } finally {
      setIsBooking(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this mentorship session?')) return;
    try {
      await studentApi.cancelBooking(bookingId);
      setBookings((prev) =>
        prev.map((b) => (b.bookingId === bookingId ? { ...b, status: 'cancelled' } : b))
      );
      await loadBookings();
      await loadDashboard();
    } catch (err) {
      alert(err.message || 'Failed to cancel booking');
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setProfileError('');
    setProfileSaved(false);

    try {
      await authApi.updateProfile({
        fullName: fullName.trim(),
        email: email.trim().toLowerCase(),
        targetDomain,
        educationLevel
      });
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 3000);
    } catch (err) {
      setProfileError(err.message || 'Failed to update profile settings');
    }
  };

  const formatSlotTime = (isoString) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC';
    } catch {
      return isoString;
    }
  };

  // Group conversations chronologically (Today, Yesterday, Previous 7 Days, Older)
  const groupConversations = (convList) => {
    const groups = { Today: [], Yesterday: [], 'Previous 7 Days': [], Older: [] };
    const now = new Date();
    const todayStr = now.toISOString().split('T')[0];

    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];

    const weekAgo = new Date(now);
    weekAgo.setDate(weekAgo.getDate() - 7);

    convList.forEach((conv) => {
      const convDate = new Date(conv.updatedAt || conv.createdAt);
      const dateStr = convDate.toISOString().split('T')[0];

      if (dateStr === todayStr) {
        groups.Today.push(conv);
      } else if (dateStr === yesterdayStr) {
        groups.Yesterday.push(conv);
      } else if (convDate >= weekAgo) {
        groups['Previous 7 Days'].push(conv);
      } else {
        groups.Older.push(conv);
      }
    });

    return groups;
  };

  const filteredConversations = conversations.filter((c) =>
    (c.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );
  const groupedConvs = groupConversations(filteredConversations);

  // Extract latest recommendations from the chat messages
  const latestAssistantMsgWithRecs = [...chatMessages]
    .reverse()
    .find((m) => m.role === 'assistant' && m.recommendations && m.recommendations.length > 0);
  const latestRecs = latestAssistantMsgWithRecs?.recommendations || [];

  return (
    <div className="space-y-6">
      {/* ========================================================================= */}
      {/* TAB 1: CHAT-FIRST CAREER ADVISOR WORKSPACE (3 PANELS ON DESKTOP) */}
      {/* ========================================================================= */}
      {activeTab === 'chat' && (
        <div className="flex flex-col md:flex-row gap-5 items-stretch min-h-[680px]">
          {/* PANEL 1: CONVERSATION SIDEBAR (270px) */}
          <div
            className={`w-full md:w-[280px] shrink-0 bg-white rounded-xl border border-[#E4E7EC] shadow-xs flex flex-col p-3.5 transition-all ${
              sidebarOpen ? 'block' : 'hidden md:flex'
            }`}
          >
            {/* Mobile Header with Close Button */}
            <div className="flex items-center justify-between md:hidden pb-2 mb-2 border-b border-[#E4E7EC]">
              <span className="text-xs font-bold text-[#202124]">Conversations</span>
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1 rounded text-[#667085] hover:text-[#202124] hover:bg-[#F8F9FA]"
                aria-label="Close sidebar"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* New Chat Button */}
            <button
              onClick={handleNewChat}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-3 bg-[#315E9E] hover:bg-[#26497B] text-white rounded-lg text-sm font-semibold transition shadow-xs cursor-pointer mb-3"
            >
              <Plus className="w-4 h-4" />
              <span>New Conversation</span>
            </button>

            {/* Search Conversations Input */}
            <div className="relative mb-3">
              <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-[#98A2B3]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conversations..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#F8F9FA] border border-[#E4E7EC] rounded-lg text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:bg-white transition"
              />
            </div>

            {/* Conversation Group List */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {filteredConversations.length === 0 ? (
                <div className="text-center py-8 text-xs text-[#667085]">
                  No conversation history found.
                </div>
              ) : (
                Object.entries(groupedConvs).map(([groupTitle, convList]) => {
                  if (convList.length === 0) return null;
                  return (
                    <div key={groupTitle} className="space-y-1">
                      <div className="text-[11px] font-semibold text-[#98A2B3] uppercase tracking-wider px-2 py-1">
                        {groupTitle}
                      </div>
                      {convList.map((conv) => {
                        const isSelected = activeConvId === conv.conversationId;
                        return (
                          <div
                            key={conv.conversationId}
                            onClick={() => handleSelectConversation(conv.conversationId)}
                            className={`group flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium cursor-pointer transition ${
                              isSelected
                                ? 'bg-[#EFF4FA] text-[#315E9E] font-semibold border border-[#D0DCEB]'
                                : 'text-[#344054] hover:bg-[#F8F9FA]'
                            }`}
                          >
                            <span className="truncate pr-2">
                              {conv.title || 'Career Conversation'}
                            </span>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition shrink-0">
                              <button
                                onClick={(e) => handleStartRename(conv, e)}
                                title="Rename"
                                className="p-1 text-[#667085] hover:text-[#315E9E] rounded hover:bg-white"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                              <button
                                onClick={(e) => handleDeleteConversation(conv.conversationId, e)}
                                title="Delete"
                                className="p-1 text-[#667085] hover:text-[#D92D20] rounded hover:bg-white"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* PANEL 2: CENTER MAIN CHAT WORKSPACE */}
          <div className="flex-1 bg-white rounded-xl border border-[#E4E7EC] shadow-xs flex flex-col overflow-hidden min-h-[640px]">
            {/* Chat Workspace Header */}
            <div className="p-4 border-b border-[#E4E7EC] flex items-center justify-between bg-white">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="md:hidden flex items-center justify-center p-2 rounded-lg text-[#315E9E] bg-[#EFF4FA] border border-[#D0DCEB] hover:bg-[#E0ECF8] cursor-pointer"
                  title="Toggle conversation list"
                  aria-label="Toggle conversation history"
                >
                  <MessageSquare className="w-4 h-4" />
                </button>
                <div className="w-9 h-9 rounded-lg bg-[#EFF4FA] text-[#315E9E] flex items-center justify-center font-bold text-sm">
                  <Sparkles className="w-4 h-4 text-[#315E9E]" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[#202124] leading-tight">
                    {conversations.find((c) => c.conversationId === activeConvId)?.title ||
                      'Career Mentorship Advisor'}
                  </h2>
                  <p className="text-xs text-[#667085] leading-tight">
                    Verified mentorship recommendations based on real profile data
                  </p>
                </div>
              </div>

              {activeConvId && (
                <button
                  onClick={handleNewChat}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#315E9E] bg-[#EFF4FA] hover:bg-[#E0ECF8] rounded-lg transition cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">New Chat</span>
                </button>
              )}
            </div>

            {/* Error Banner (Friendly Guardrail / Validation display) */}
            {errorMsg && (
              <div className="p-3 bg-amber-50 border-b border-amber-200 text-[#B54708] text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-[#F79009]" />
                  <span>{errorMsg}</span>
                </div>
                <button onClick={() => setErrorMsg('')} className="text-[#B54708] hover:underline">
                  Dismiss
                </button>
              </div>
            )}

            {/* Chat Messages Scrolling Feed */}
            <div className="flex-1 p-5 overflow-y-auto space-y-5 bg-[#FDFDFE]">
              {chatMessages.length === 0 ? (
                /* Welcome Initial Empty State */
                <div className="max-w-xl mx-auto my-auto text-center py-10 space-y-4">
                  <div className="w-12 h-12 rounded-xl bg-[#EFF4FA] text-[#315E9E] flex items-center justify-center mx-auto shadow-xs">
                    <Sparkles className="w-6 h-6 text-[#315E9E]" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-[#202124]">
                      Welcome to your Career Workspace
                    </h3>
                    <p className="text-sm text-[#667085] mt-1 max-w-md mx-auto">
                      Ask any question about breaking into tech, preparing for interviews, or finding a verified mentor matching your goals.
                    </p>
                  </div>

                  {/* Suggestion Prompts */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-2 text-left">
                    {[
                      'I want to break into AI product management and learn LLMs.',
                      'Find me senior engineering mentors in Bengaluru with startup experience.',
                      'How do I prepare for technical product manager interviews?',
                      'Which mentors can guide me on venture capital and fundraising?'
                    ].map((promptText, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => {
                          setInputQuery(promptText);
                          setTimeout(() => chatInputRef.current?.focus(), 50);
                        }}
                        className="p-3 rounded-lg border border-[#E4E7EC] bg-white hover:bg-[#F8F9FA] hover:border-[#315E9E]/40 text-xs text-[#344054] transition cursor-pointer text-left"
                      >
                        {promptText}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Render Chat Message Thread */
                chatMessages.map((msg, idx) => {
                  const isUser = msg.role === 'user';
                  const recs = msg.recommendations || [];

                  return (
                    <div
                      key={msg.messageId || idx}
                      className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-xl p-4 text-sm leading-relaxed ${
                          isUser
                            ? 'bg-[#EFF4FA] text-[#202124] border border-[#D0DCEB]'
                            : 'bg-white text-[#202124] border border-[#E4E7EC] shadow-xs'
                        }`}
                      >
                        {/* Assistant label */}
                        {!isUser && (
                          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#315E9E] mb-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-[#315E9E]" />
                            <span>Mentor Connect Advisor</span>
                          </div>
                        )}
                        <p className="whitespace-pre-line">{msg.content}</p>
                      </div>

                      {/* Display inline recommendation preview if on mobile */}
                      {!isUser && recs.length > 0 && (
                        <div className="w-full mt-3 block lg:hidden">
                          <span className="text-xs font-bold text-[#667085] block mb-2">
                            Recommended Mentors ({recs.length}):
                          </span>
                          <div className="space-y-3">
                            {recs.map((rec) => (
                              <MentorRecommendationCard
                                key={rec.mentorId}
                                mentor={rec}
                                onBook={() => handleOpenBooking(rec)}
                                isExpanded={expandedMentors[rec.mentorId]}
                                onToggleExpand={() => toggleMentorExpand(rec.mentorId)}
                              />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}

              {isSending && (
                <div className="flex items-center gap-3 p-4 max-w-md bg-white border border-[#E4E7EC] rounded-xl text-sm text-[#667085] shadow-xs">
                  <div className="w-4 h-4 border-2 border-[#D0D5DD] border-t-[#315E9E] rounded-full animate-spin shrink-0" />
                  <span>Evaluating verified mentor profiles &amp; calculating match criteria...</span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Fixed Bottom Input Area */}
            <form
              onSubmit={handleSendMessage}
              className="p-4 bg-white border-t border-[#E4E7EC] flex gap-3 items-end"
            >
              <div className="flex-1 relative">
                <textarea
                  ref={chatInputRef}
                  rows={2}
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  placeholder="Ask a question or specify target career goals..."
                  className="w-full p-3 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:ring-2 focus:ring-[#315E9E]/15 resize-none transition"
                />
                <span className="hidden sm:block text-[11px] text-[#98A2B3] absolute right-3 bottom-2">
                  Press Enter to send, Shift+Enter for new line
                </span>
              </div>

              <button
                type="submit"
                disabled={isSending || !inputQuery.trim()}
                className="h-11 px-5 bg-[#315E9E] hover:bg-[#26497B] text-white rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition disabled:opacity-40 cursor-pointer shadow-xs shrink-0"
              >
                <span>Send</span>
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>

          {/* PANEL 3: CONTEXTUAL RECOMMENDATIONS PANEL (DESKTOP RIGHT SIDE) */}
          {latestRecs.length > 0 && (
            <div className="hidden lg:flex flex-col w-[380px] shrink-0 bg-white rounded-xl border border-[#E4E7EC] shadow-xs p-4 overflow-y-auto max-h-[780px]">
              <div className="flex items-center justify-between pb-3 border-b border-[#E4E7EC] mb-4">
                <div>
                  <h3 className="text-sm font-bold text-[#202124]">
                    Top Matched Mentors ({latestRecs.length})
                  </h3>
                  <span className="text-[11px] text-[#667085]">
                    Filtered by 100-point rubric (&ge; 30% threshold)
                  </span>
                </div>
              </div>

              <div className="space-y-4">
                {latestRecs.map((mentor) => (
                  <MentorRecommendationCard
                    key={mentor.mentorId}
                    mentor={mentor}
                    onBook={() => handleOpenBooking(mentor)}
                    isExpanded={expandedMentors[mentor.mentorId]}
                    onToggleExpand={() => toggleMentorExpand(mentor.mentorId)}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: MY BOOKINGS TAB */}
      {/* ========================================================================= */}
      {activeTab === 'bookings' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-[#202124]">My Mentorship Sessions</h2>
              <p className="text-sm text-[#667085]">Review and prepare for your upcoming sessions</p>
            </div>
          </div>

          {bookings.length === 0 ? (
            <div className="bg-white rounded-xl border border-[#E4E7EC] p-12 text-center shadow-xs">
              <Calendar className="w-12 h-12 text-[#98A2B3] mx-auto mb-3" />
              <h3 className="text-base font-semibold text-[#202124]">No bookings scheduled</h3>
              <p className="text-sm text-[#667085] mt-1 max-w-sm mx-auto">
                Ask the AI Career Advisor for recommendations and book a 1-on-1 consultation slot.
              </p>
              <button
                onClick={() => setActiveTab('chat')}
                className="mt-4 px-4 py-2 bg-[#315E9E] hover:bg-[#26497B] text-white text-xs font-semibold rounded-lg transition cursor-pointer"
              >
                Go to Advisor
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {bookings.map((b) => {
                const isCancelled = b.status === 'cancelled';
                const isCompleted = b.status === 'completed';

                return (
                  <div
                    key={b.bookingId}
                    className={`bg-white rounded-xl border p-5 shadow-xs transition space-y-3 ${
                      isCancelled ? 'border-rose-200 bg-rose-50/20 opacity-80' : 'border-[#E4E7EC]'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-base font-bold text-[#202124]">{b.mentorName}</h4>
                        <span className="text-xs text-[#667085] font-mono">ID: {b.mentorId}</span>
                      </div>
                      <span
                        className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${
                          isCancelled
                            ? 'bg-rose-50 text-[#D92D20] border border-rose-200'
                            : isCompleted
                            ? 'bg-gray-100 text-[#344054] border border-gray-200'
                            : b.status === 'pending'
                            ? 'bg-amber-50 text-[#B54708] border border-amber-200'
                            : 'bg-emerald-50 text-[#027A48] border border-emerald-200'
                        }`}
                      >
                        {b.status === 'pending' ? 'Pending Approval' : b.status}
                      </span>
                    </div>

                    <div className="text-xs text-[#344054] space-y-1">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-[#667085]" />
                        <span>{new Date(b.slotStart).toLocaleString()} (UTC)</span>
                      </div>
                      <div className="text-[#667085]">
                        <span className="font-semibold text-[#344054]">Topic: </span>
                        {b.topic || 'Mentorship consultation'}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-[#E4E7EC] flex items-center justify-between">
                      {b.status === 'pending' ? (
                        <span className="text-xs text-[#B54708] bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200 font-medium">
                          Awaiting Admin Approval
                        </span>
                      ) : b.meetingLink && !isCancelled ? (
                        <a
                          href={b.meetingLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#315E9E] hover:bg-[#26497B] text-white text-xs font-semibold rounded-lg transition"
                        >
                          <Video className="w-3.5 h-3.5" />
                          <span>Join Google Meet</span>
                        </a>
                      ) : (
                        <span className="text-xs text-[#98A2B3]">No active link</span>
                      )}

                      {!isCancelled && !isCompleted && (
                        <button
                          onClick={() => handleCancelBooking(b.bookingId)}
                          className="text-xs text-[#D92D20] hover:underline cursor-pointer"
                        >
                          Cancel Session
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

      {/* ========================================================================= */}
      {/* TAB 3: ACCOUNT & PROFILE SETTINGS */}
      {/* ========================================================================= */}
      {activeTab === 'profile' && (
        <div className="max-w-xl mx-auto bg-white rounded-xl border border-[#E4E7EC] p-6 shadow-xs">
          <h2 className="text-lg font-bold text-[#202124] mb-1">Student Account Settings</h2>
          <p className="text-xs text-[#667085] mb-5">
            Update your profile and active email address to receive Google Calendar invites.
          </p>

          {profileSaved && (
            <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-[#027A48] text-xs font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#12B76A]" />
              <span>Profile settings successfully saved!</span>
            </div>
          )}

          {profileError && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-[#D92D20] text-xs font-medium">
              {profileError}
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Full Name</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">
                Email Address (Receives Google Calendar Invites)
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#344054] mb-1.5">Target Domain</label>
                <select
                  value={targetDomain}
                  onChange={(e) => setTargetDomain(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
                >
                  <option value="Artificial Intelligence">Artificial Intelligence</option>
                  <option value="Product Management">Product Management</option>
                  <option value="Software Engineering">Software Engineering</option>
                  <option value="Data Science & Analytics">Data Science & Analytics</option>
                  <option value="Venture Capital & Startups">Venture Capital & Startups</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#344054] mb-1.5">Education Level</label>
                <select
                  value={educationLevel}
                  onChange={(e) => setEducationLevel(e.target.value)}
                  className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
                >
                  <option value="Undergraduate">Undergraduate</option>
                  <option value="Postgraduate">Postgraduate</option>
                  <option value="Early Professional">Early Professional</option>
                  <option value="Career Switcher">Career Switcher</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 px-4 bg-[#315E9E] hover:bg-[#26497B] text-white font-semibold rounded-lg text-sm transition cursor-pointer shadow-xs"
            >
              Save Profile Changes
            </button>
          </form>
        </div>
      )}

      {/* ========================================================================= */}
      {/* RENAME CONVERSATION MODAL */}
      {/* ========================================================================= */}
      {renamingConvId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-[#E4E7EC] p-5 max-w-sm w-full shadow-lg space-y-4">
            <h3 className="text-base font-bold text-[#202124]">Rename Conversation</h3>
            <form onSubmit={handleSaveRename} className="space-y-3">
              <input
                type="text"
                required
                maxLength={60}
                value={newTitleInput}
                onChange={(e) => setNewTitleInput(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setRenamingConvId(null)}
                  className="px-3 py-1.5 text-xs font-medium text-[#667085] hover:bg-[#F2F4F7] rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 text-xs font-semibold bg-[#315E9E] hover:bg-[#26497B] text-white rounded-lg"
                >
                  Save Title
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* BOOKING MODAL WITH FIX FOR SLOT SELECTION BUG (PHASE 4) */}
      {/* ========================================================================= */}
      {bookingModalMentor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-[#E4E7EC] p-6 max-w-md w-full shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between pb-3 border-b border-[#E4E7EC]">
              <div>
                <span className="text-[11px] font-bold text-[#315E9E] uppercase tracking-wider block">
                  Schedule Mentorship Consultation
                </span>
                <h3 className="text-lg font-bold text-[#202124]">{bookingModalMentor.name}</h3>
                <span className="text-xs text-[#667085]">
                  {bookingModalMentor.company} &bull; {bookingModalMentor.domain}
                </span>
              </div>
              <button
                onClick={() => setBookingModalMentor(null)}
                className="p-1 rounded-lg text-[#667085] hover:text-[#202124] hover:bg-[#F2F4F7]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {bookingSuccess ? (
              <div className="py-6 text-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto text-[#B54708]">
                  <Clock className="w-6 h-6 text-[#B54708]" />
                </div>
                <h4 className="text-base font-bold text-[#202124]">Booking Request Submitted!</h4>
                <div className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-[#B54708] border border-amber-200">
                  Pending Admin Approval
                </div>
                <p className="text-xs text-[#667085] max-w-sm mx-auto">
                  Your session request for {new Date(bookingSuccess.slotStart).toLocaleString()} (UTC) has been submitted and is currently in <strong>Pending Approval</strong> mode.
                  The platform administrator will review and approve your session. You will receive an email confirmation once approved.
                </p>
                <div className="pt-3">
                  <button
                    onClick={() => {
                      setBookingModalMentor(null);
                      setActiveTab('bookings');
                    }}
                    className="px-4 py-2 bg-[#315E9E] text-white text-xs font-semibold rounded-lg hover:bg-[#26497B] shadow-xs cursor-pointer"
                  >
                    View in My Bookings
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {bookingConflictError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-[#D92D20] text-xs rounded-lg flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{bookingConflictError}</span>
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-[#344054] mb-1">
                    Select Consultation Date
                  </label>
                  <input
                    type="date"
                    value={bookingDate}
                    min={new Date().toISOString().split('T')[0]}
                    onChange={handleDateChange}
                    className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#344054] mb-1">Topic / Goals</label>
                  <input
                    type="text"
                    value={bookingTopic}
                    onChange={(e) => setBookingTopic(e.target.value)}
                    placeholder="E.g. Transitioning from engineering to product management"
                    className="w-full px-3 py-2 text-sm bg-white border border-[#D0D5DD] rounded-lg text-[#202124] focus:outline-none focus:border-[#315E9E]"
                  />
                </div>

                {/* Available vs Booked Slots Grid */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-semibold text-[#344054]">
                      Available Time Slots (30 min)
                    </label>
                    <span className="text-[11px] text-[#667085]">Times shown in UTC</span>
                  </div>

                  {loadingSlots ? (
                    <div className="text-center py-6 text-xs text-[#667085] animate-pulse">
                      Checking real-time slot availability...
                    </div>
                  ) : rawSlots.length === 0 ? (
                    <div className="text-center py-6 text-xs text-[#667085] border border-dashed border-[#D0D5DD] rounded-lg">
                      No slots available for this date.
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-1">
                      {rawSlots.map((slot, idx) => {
                        const isAvailable = slot.isAvailable !== false;
                        const startLabel = formatSlotTime(slot.slotStart);
                        // Strict single-slot comparison fix (no undefined === undefined bug!)
                        const isSelected = Boolean(
                          selectedSlot &&
                          selectedSlot.slotStart &&
                          slot.slotStart &&
                          selectedSlot.slotStart === slot.slotStart
                        );

                        if (!isAvailable) {
                          return (
                            <div
                              key={slot.slotStart || idx}
                              className="p-2.5 rounded-lg border border-[#E4E7EC] bg-[#F8F9FA] text-[#98A2B3] text-xs font-mono flex items-center justify-between cursor-not-allowed select-none"
                              title="This time slot is already booked"
                            >
                              <span>{startLabel}</span>
                              <span className="text-[10px] uppercase font-bold text-[#D92D20]">
                                Booked
                              </span>
                            </div>
                          );
                        }

                        return (
                          <button
                            key={slot.slotStart || idx}
                            type="button"
                            onClick={() => handleSelectSlot(slot)}
                            className={`p-2.5 rounded-lg border text-xs font-mono font-medium flex items-center justify-between transition cursor-pointer ${
                              isSelected
                                ? 'bg-[#EFF4FA] border-[#315E9E] text-[#315E9E] font-bold ring-2 ring-[#315E9E]/20 shadow-xs'
                                : 'bg-white border-[#D0D5DD] text-[#344054] hover:bg-[#F8F9FA]'
                            }`}
                          >
                            <span>{startLabel}</span>
                            <span className="text-[10px] uppercase font-bold text-[#12B76A]">
                              Available
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Selected Slot Confirmation Summary */}
                {selectedSlot && (
                  <div className="p-3 bg-[#EFF4FA] border border-[#D0DCEB] rounded-lg text-xs space-y-1">
                    <div className="font-semibold text-[#315E9E] flex items-center gap-1.5">
                      <Check className="w-3.5 h-3.5 text-[#315E9E]" />
                      <span>Selected Slot: {formatSlotTime(selectedSlot.slotStart)} on {bookingDate}</span>
                    </div>
                    <span className="text-[#667085] block">Duration: 30 minutes consultation</span>
                  </div>
                )}

                <div className="pt-3 border-t border-[#E4E7EC] flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setBookingModalMentor(null)}
                    className="px-4 py-2 text-xs font-medium text-[#667085] hover:bg-[#F2F4F7] rounded-lg"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleConfirmBooking}
                    disabled={isBooking || !selectedSlot}
                    className="px-5 py-2 bg-[#315E9E] hover:bg-[#26497B] text-white font-semibold text-xs rounded-lg transition disabled:opacity-40 shadow-xs cursor-pointer"
                  >
                    {isBooking ? 'Confirming...' : 'Confirm Booking'}
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

// =============================================================================
// SUB-COMPONENT: STRUCTURED MENTOR RECOMMENDATION CARD (PHASE 2)
// =============================================================================
function MentorRecommendationCard({ mentor, onBook, isExpanded, onToggleExpand }) {
  const scoreBreakdown = mentor.scoreBreakdown || {};
  const toolExperience = mentor.toolExperience || {};
  const aiProfile = mentor.aiProfile || {};

  return (
    <div className="bg-white rounded-xl border border-[#E4E7EC] p-4 shadow-xs hover:border-[#315E9E]/40 transition space-y-3">
      {/* Header with Name, Role, Location, Match % */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-[#202124]">{mentor.name}</h4>
            <span className="text-[11px] font-mono text-[#98A2B3]">[{mentor.mentorId}]</span>
          </div>
          <span className="text-xs text-[#667085] font-medium block">
            {mentor.company || 'Enterprise Leader'} &bull; {mentor.domain}
          </span>
          <div className="flex items-center gap-3 mt-1 text-[11px] text-[#667085]">
            <span className="flex items-center gap-1">
              <MapPin className="w-3 h-3 text-[#98A2B3]" />
              {mentor.city || 'Global'}
            </span>
            <span className="flex items-center gap-1">
              <Award className="w-3 h-3 text-[#98A2B3]" />
              {mentor.seniority || 'Experienced'}
            </span>
          </div>
        </div>

        {/* Real Match Score Badge */}
        <div className="text-right shrink-0">
          <span className="inline-block px-2.5 py-1 bg-[#EFF4FA] border border-[#D0DCEB] text-[#315E9E] rounded-lg text-xs font-bold shadow-xs">
            {mentor.matchPercentage || 75}% Match
          </span>
          <span className="block text-[10px] text-[#98A2B3] mt-0.5">100-pt Rubric</span>
        </div>
      </div>

      {/* Why this mentor fits your goal */}
      <div className="p-3 bg-[#F8F9FA] rounded-lg text-xs space-y-1">
        <span className="font-semibold text-[#202124] block">Why this mentor fits your goal:</span>
        <p className="text-[#344054] leading-relaxed">{mentor.matchReason}</p>
      </div>

      {/* Relevant Evidence */}
      {mentor.relevantExperience && (
        <div className="text-xs text-[#667085]">
          <span className="font-semibold text-[#344054]">Relevant Evidence: </span>
          <span>{mentor.relevantExperience}</span>
        </div>
      )}

      {/* Expertise Chips */}
      {mentor.rolesOfExpertise && mentor.rolesOfExpertise.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1">
          {mentor.rolesOfExpertise.map((role, i) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-[#F2F4F7] text-[#344054] text-[11px] font-medium rounded-md"
            >
              {role}
            </span>
          ))}
        </div>
      )}

      {/* Limitations / Potential Gap */}
      {mentor.limitations && (
        <div className="text-[11px] text-[#667085] flex items-start gap-1.5 bg-amber-50/50 p-2 rounded-md border border-amber-200/40">
          <Info className="w-3.5 h-3.5 text-[#F79009] shrink-0 mt-0.5" />
          <span>
            <strong className="text-[#344054]">Potential Gap / Notes:</strong> {mentor.limitations}
          </span>
        </div>
      )}

      {/* Expandable Details Toggle */}
      <button
        type="button"
        onClick={onToggleExpand}
        className="w-full flex items-center justify-between pt-2 border-t border-[#E4E7EC] text-xs font-semibold text-[#315E9E] hover:text-[#26497B] cursor-pointer"
      >
        <span>{isExpanded ? 'Hide Detailed Profile' : 'View Full Profile Details'}</span>
        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      {/* Expanded Profile Details */}
      {isExpanded && (
        <div className="space-y-3 pt-2 text-xs border-t border-dashed border-[#E4E7EC]">
          {/* 100-Point Rubric Breakdown */}
          {scoreBreakdown && Object.keys(scoreBreakdown).length > 0 && (
            <div className="space-y-1.5">
              <span className="font-bold text-[#202124] block">Match Rubric Breakdown (out of 100):</span>
              <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                <div className="p-1.5 bg-[#F8F9FA] rounded">
                  Skill Relevance: <strong>{scoreBreakdown.expertiseSkillScore || 0}/40</strong>
                </div>
                <div className="p-1.5 bg-[#F8F9FA] rounded">
                  Domain Alignment: <strong>{scoreBreakdown.domainAlignmentScore || 0}/25</strong>
                </div>
                <div className="p-1.5 bg-[#F8F9FA] rounded">
                  Role &amp; Seniority: <strong>{scoreBreakdown.roleSeniorityScore || 0}/15</strong>
                </div>
                <div className="p-1.5 bg-[#F8F9FA] rounded">
                  Mentorship Quality: <strong>{scoreBreakdown.mentorshipQualityScore || 0}/10</strong>
                </div>
                <div className="p-1.5 bg-[#F8F9FA] rounded col-span-2">
                  Tool &amp; AI Capability: <strong>{scoreBreakdown.toolAiScore || 0}/10</strong>
                </div>
              </div>
            </div>
          )}

          {/* AI Subdomains & Tools */}
          {aiProfile && (aiProfile.tools?.length > 0 || aiProfile.subdomains?.length > 0) && (
            <div className="space-y-1">
              <span className="font-semibold text-[#344054]">AI Tools &amp; Workflows:</span>
              <div className="flex flex-wrap gap-1">
                {(aiProfile.tools || []).map((t, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 bg-[#EFF4FA] text-[#315E9E] rounded text-[10px] font-mono"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Tool Experience Matrix */}
          <div>
            <span className="font-semibold text-[#344054] block mb-1">
              Standard Tools Experience:
            </span>
            <div className="grid grid-cols-3 gap-1 text-[10px]">
              {['Tableau', 'HubSpot', 'Google Analytics', 'Jira', 'Excel', 'Mixpanel'].map(
                (toolName) => {
                  const key = toolName.toLowerCase().replace(/\s+/g, '');
                  const hasExp = toolExperience[key] || toolExperience[toolName.toLowerCase()];
                  return (
                    <span
                      key={toolName}
                      className={`px-1.5 py-1 rounded text-center font-medium ${
                        hasExp === true
                          ? 'bg-emerald-50 text-[#027A48] border border-emerald-200'
                          : 'bg-gray-50 text-[#667085] border border-gray-200'
                      }`}
                    >
                      {toolName}: {hasExp === true ? 'Recorded' : 'Unlisted'}
                    </span>
                  );
                }
              )}
            </div>
          </div>

          {/* Mentorship Quality */}
          {mentor.mentorshipQuality && (
            <div className="text-[11px] text-[#667085]">
              <span className="font-semibold text-[#344054]">Verified Mentorship Rating: </span>
              <span className="capitalize text-[#315E9E] font-bold">
                {mentor.mentorshipQuality}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="pt-2">
        <button
          type="button"
          onClick={onBook}
          className="w-full py-2 px-3 bg-[#315E9E] hover:bg-[#26497B] text-white text-xs font-semibold rounded-lg transition shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
        >
          <CalendarCheck className="w-3.5 h-3.5" />
          <span>Book 1-on-1 Consultation</span>
        </button>
      </div>
    </div>
  );
}

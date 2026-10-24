const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL.replace(/\/$/, '')}/api`
  : '/api';

export function getToken() {
  return localStorage.getItem('guided_token');
}

export function setToken(token) {
  if (token) {
    localStorage.setItem('guided_token', token);
  } else {
    localStorage.removeItem('guided_token');
  }
}

export async function apiRequest(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (response.status === 401) {
    setToken(null);
    if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
      window.location.href = '/login?expired=1';
    }
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = data?.detail || response.statusText || 'Request failed';
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

// Authentication API
export const authApi = {
  login: (credentials) => apiRequest('/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  register: (payload) => apiRequest('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  getMe: () => apiRequest('/auth/me'),
  updateProfile: (payload) => apiRequest('/auth/profile', { method: 'PUT', body: JSON.stringify(payload) })
};

// Student API
export const studentApi = {
  getDashboard: () => apiRequest('/student/dashboard'),
  getBookings: (status) => apiRequest(`/student/bookings${status ? `?status=${status}` : ''}`),
  getConversations: () => apiRequest('/student/conversations'),
  getConversation: (convId) => apiRequest(`/chat/conversations/${convId}`),
  createConversation: (payload) => apiRequest('/chat/conversations', { method: 'POST', body: JSON.stringify(payload) }),
  sendMessage: (convId, message) => apiRequest(`/chat/conversations/${convId}/messages`, { method: 'POST', body: JSON.stringify({ message }) }),
  updateConversationTitle: (convId, title) => apiRequest(`/chat/conversations/${convId}/title`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  deleteConversation: (convId) => apiRequest(`/chat/conversations/${convId}`, { method: 'DELETE' }),
  getRecommendations: (query, k = 5) => apiRequest('/agent/recommend', { method: 'POST', body: JSON.stringify({ query, top_k: k }) }),
  getMentorSlots: (mentorId, targetDate, duration = 30) => apiRequest(`/bookings/mentors/${mentorId}/slots?target_date=${targetDate}&duration_minutes=${duration}`),
  bookSlot: (payload) => apiRequest('/bookings', { method: 'POST', body: JSON.stringify(payload) }),
  cancelBooking: (bookingId) => apiRequest(`/bookings/${bookingId}/cancel`, { method: 'POST' })
};

// Mentor API
export const mentorApi = {
  getDashboard: () => apiRequest('/mentor/dashboard'),
  getBookings: (status) => apiRequest(`/mentor/bookings${status ? `?status=${status}` : ''}`),
  getBookingDetail: (bookingId) => apiRequest(`/mentor/bookings/${bookingId}`),
  getStudentContext: (bookingId) => apiRequest(`/mentor/bookings/${bookingId}/student-context`),
  updateStatus: (bookingId, status) => apiRequest(`/mentor/bookings/${bookingId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  getProfile: () => apiRequest('/mentor/profile'),
  updateProfile: (payload) => apiRequest('/mentor/profile', { method: 'PUT', body: JSON.stringify(payload) })
};

// Admin API
export const adminApi = {
  getStats: () => apiRequest('/admin/dashboard/stats'),
  getUsers: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/admin/users${qs ? `?${qs}` : ''}`);
  },
  updateUserRole: (userId, role) => apiRequest(`/admin/users/${userId}/role`, { method: 'PATCH', body: JSON.stringify({ role }) }),
  updateUserStatus: (userId, status) => apiRequest(`/admin/users/${userId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  getBookings: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/admin/bookings${qs ? `?${qs}` : ''}`);
  },
  updateBookingStatus: (bookingId, status) => apiRequest(`/admin/bookings/${bookingId}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  approveBooking: (bookingId) => apiRequest(`/admin/bookings/${bookingId}/approve`, { method: 'POST' }),
  rejectBooking: (bookingId) => apiRequest(`/admin/bookings/${bookingId}/reject`, { method: 'POST' }),
  getAuditLogs: (page = 1, limit = 20) => apiRequest(`/admin/audit-logs?page=${page}&limit=${limit}`),
  getHealth: () => apiRequest('/admin/health')
};

// Mentors Public Directory API
export const mentorsApi = {
  getAll: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest(`/mentors${qs ? `?${qs}` : ''}`);
  },
  getById: (mentorId) => apiRequest(`/mentors/${mentorId}`)
};

// Deterministic Mentor Password generator
export function getMentorPassword(mentorId) {
  if (!mentorId) return '';
  const clean = mentorId.trim().toUpperCase();
  return `Mentor@${clean}!123`;
}


import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, User, GraduationCap, Briefcase, ArrowRight } from 'lucide-react';

export default function Register() {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [targetDomain, setTargetDomain] = useState('Artificial Intelligence');
  const [educationLevel, setEducationLevel] = useState('Undergraduate');
  const [mentorId, setMentorId] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const payload = {
        fullName: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        role,
        targetDomain,
        educationLevel: role === 'student' ? educationLevel : undefined,
        mentorId: role === 'mentor' && mentorId ? mentorId.trim().toUpperCase() : undefined
      };

      const user = await register(payload);
      if (user.role === 'mentor') {
        navigate('/mentor', { replace: true });
      } else {
        navigate('/student', { replace: true });
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Please check your details.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#202124] flex flex-col justify-center py-12 px-4 sm:px-6 font-sans">
      {/* Brand Header */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center mb-6">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#315E9E] text-white font-bold text-lg mb-3 shadow-xs">
          MC
        </div>
        <h1 className="text-2xl font-bold text-[#202124] tracking-tight">
          Create Account
        </h1>
        <p className="text-sm text-[#667085] mt-1">
          Join Mentor Connect to accelerate your career
        </p>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 rounded-xl sm:px-8 shadow-sm border border-[#E4E7EC]">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-[#D92D20] text-xs font-medium">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Registering As</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole('student')}
                  className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs font-semibold transition-all cursor-pointer ${
                    role === 'student'
                      ? 'bg-[#EFF4FA] border-[#315E9E] text-[#315E9E]'
                      : 'bg-white border-[#D0D5DD] text-[#667085] hover:bg-[#F9FAFB]'
                  }`}
                >
                  <GraduationCap className="w-4 h-4" />
                  <span>Student</span>
                </button>

                <button
                  type="button"
                  onClick={() => setRole('mentor')}
                  className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs font-semibold transition-all cursor-pointer ${
                    role === 'mentor'
                      ? 'bg-[#ECFDF3] border-[#12B76A] text-[#027A48]'
                      : 'bg-white border-[#D0D5DD] text-[#667085] hover:bg-[#F9FAFB]'
                  }`}
                >
                  <Briefcase className="w-4 h-4" />
                  <span>Mentor</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Full Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <User className="h-4 w-4 text-[#98A2B3]" />
                </div>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Aarav Mehta"
                  className="block w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:ring-2 focus:ring-[#315E9E]/15 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-[#98A2B3]" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@domain.com"
                  className="block w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:ring-2 focus:ring-[#315E9E]/15 transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#344054] mb-1.5">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-[#98A2B3]" />
                </div>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="block w-full pl-10 pr-3.5 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] placeholder-[#98A2B3] focus:outline-none focus:border-[#315E9E] focus:ring-2 focus:ring-[#315E9E]/15 transition"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#344054] mb-1.5">Domain</label>
                <select
                  value={targetDomain}
                  onChange={(e) => setTargetDomain(e.target.value)}
                  className="block w-full px-3 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
                >
                  <option value="Artificial Intelligence">Artificial Intelligence</option>
                  <option value="Product Management">Product Management</option>
                  <option value="Software Engineering">Software Engineering</option>
                  <option value="Data Science & Analytics">Data Science & Analytics</option>
                  <option value="Venture Capital & Startups">Venture Capital & Startups</option>
                </select>
              </div>

              {role === 'student' ? (
                <div>
                  <label className="block text-xs font-semibold text-[#344054] mb-1.5">Education</label>
                  <select
                    value={educationLevel}
                    onChange={(e) => setEducationLevel(e.target.value)}
                    className="block w-full px-3 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] focus:outline-none focus:border-[#315E9E]"
                  >
                    <option value="Undergraduate">Undergraduate</option>
                    <option value="Postgraduate">Postgraduate</option>
                    <option value="Early Professional">Early Professional</option>
                    <option value="Career Switcher">Career Switcher</option>
                  </select>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-[#344054] mb-1.5">Mentor ID (Optional)</label>
                  <input
                    type="text"
                    value={mentorId}
                    onChange={(e) => setMentorId(e.target.value)}
                    placeholder="M001"
                    className="block w-full px-3 py-2.5 bg-white border border-[#D0D5DD] rounded-lg text-sm text-[#202124] placeholder-[#98A2B3] uppercase focus:outline-none focus:border-[#315E9E]"
                  />
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-3 flex justify-center items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-[#315E9E] hover:bg-[#26497B] transition disabled:opacity-50 cursor-pointer shadow-xs"
            >
              <span>{isSubmitting ? 'Registering...' : 'Register'}</span>
              <ArrowRight className="w-4 h-4 text-white" />
            </button>
          </form>

          <div className="mt-5 text-center">
            <span className="text-xs text-[#667085]">Already registered? </span>
            <Link to="/login" className="text-xs font-semibold text-[#315E9E] hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

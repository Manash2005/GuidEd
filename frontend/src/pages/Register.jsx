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
    <div className="min-h-screen bg-[#090E0A] text-[#F1F6F2] flex flex-col justify-center py-12 px-4 sm:px-6 relative overflow-hidden font-sans">
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#5D9253]/15 blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 -right-40 w-[500px] h-[500px] rounded-full bg-[#FFCB3D]/10 blur-[150px] pointer-events-none" />

      {/* Brand - text only */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center relative z-10 mb-6">
        <h1 className="text-3xl font-extrabold text-[#F1F6F2] tracking-tight">
          Guid<span className="text-[#FFCB3D]">Ed</span>
        </h1>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="glass-panel-elevated py-8 px-6 rounded-3xl sm:px-8 shadow-2xl border border-[#557945]/30">
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium">
              {error}
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Registering As</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole('student')}
                  className={`flex items-center justify-center gap-2 p-2.5 rounded-xl border text-xs font-bold transition-all ${
                    role === 'student'
                      ? 'bg-[#F1A344]/20 border-[#F1A344] text-[#F1A344] shadow-sm'
                      : 'bg-[#121E15] border-[#557945]/30 text-[#8BA190] hover:bg-[#18291C]'
                  }`}
                >
                  <GraduationCap className="w-4 h-4" />
                  <span>Student</span>
                </button>

                <button
                  type="button"
                  onClick={() => setRole('mentor')}
                  className={`flex items-center justify-center gap-2 p-2.5 rounded-xl border text-xs font-bold transition-all ${
                    role === 'mentor'
                      ? 'bg-[#5D9253]/20 border-[#5D9253] text-[#84CC78] shadow-sm'
                      : 'bg-[#121E15] border-[#557945]/30 text-[#8BA190] hover:bg-[#18291C]'
                  }`}
                >
                  <Briefcase className="w-4 h-4" />
                  <span>Mentor</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Full Name</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <User className="h-4 w-4 text-[#557945]" />
                </div>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your Name"
                  className="block w-full pl-10 pr-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-[#557945]" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@domain.com"
                  className="block w-full pl-10 pr-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-[#557945]" />
                </div>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="block w-full pl-10 pr-3.5 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Domain</label>
                <select
                  value={targetDomain}
                  onChange={(e) => setTargetDomain(e.target.value)}
                  className="block w-full px-3 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
                >
                  <option value="Artificial Intelligence" className="bg-[#0E1610]">Artificial Intelligence</option>
                  <option value="Product Management" className="bg-[#0E1610]">Product Management</option>
                  <option value="Software Engineering" className="bg-[#0E1610]">Software Engineering</option>
                  <option value="Data Science & Analytics" className="bg-[#0E1610]">Data Science & Analytics</option>
                  <option value="Venture Capital & Startups" className="bg-[#0E1610]">Venture Capital & Startups</option>
                </select>
              </div>

              {role === 'student' ? (
                <div>
                  <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Education</label>
                  <select
                    value={educationLevel}
                    onChange={(e) => setEducationLevel(e.target.value)}
                    className="block w-full px-3 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] focus:outline-none"
                  >
                    <option value="Undergraduate" className="bg-[#0E1610]">Undergraduate</option>
                    <option value="Postgraduate" className="bg-[#0E1610]">Postgraduate</option>
                    <option value="Early Professional" className="bg-[#0E1610]">Early Professional</option>
                    <option value="Career Switcher" className="bg-[#0E1610]">Career Switcher</option>
                  </select>
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-semibold text-[#D0DDD2] mb-1.5">Mentor ID (Optional)</label>
                  <input
                    type="text"
                    value={mentorId}
                    onChange={(e) => setMentorId(e.target.value)}
                    placeholder="M001"
                    className="block w-full px-3 py-2.5 glass-input rounded-xl text-xs text-[#F1F6F2] placeholder-[#557945] uppercase focus:outline-none"
                  />
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-3 flex justify-center items-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold text-[#090E0A] bg-gradient-to-r from-[#FFCB3D] via-[#F1A344] to-[#FFCB3D] hover:brightness-105 shadow-md shadow-[#FFCB3D]/15 transition disabled:opacity-50 cursor-pointer"
            >
              <span>{isSubmitting ? 'Registering...' : 'Register'}</span>
              <ArrowRight className="w-4 h-4 text-[#090E0A]" />
            </button>
          </form>

          <div className="mt-5 text-center">
            <span className="text-xs text-[#8BA190]">Already registered? </span>
            <Link to="/login" className="text-xs font-semibold text-[#FFCB3D] hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

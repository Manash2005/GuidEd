import React from 'react';
import Navbar from './Navbar';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[#F8F9FA] text-[#202124] flex flex-col font-sans selection:bg-[#EFF4FA] selection:text-[#315E9E]">
      {/* Top Header */}
      <Navbar />

      {/* Main Content Area */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 pt-20 pb-12">
        {children}
      </main>

      {/* Clean Professional Footer */}
      <footer className="border-t border-[#E4E7EC] bg-white py-5 text-center text-xs text-[#667085]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#315E9E]" />
            <span className="font-semibold text-[#202124]">Mentor Connect</span>
            <span className="text-[#98A2B3]">&bull;</span>
            <span className="text-xs text-[#667085]">Career Mentorship Platform</span>
          </div>
          <div className="text-xs text-[#667085]">
            &copy; {new Date().getFullYear()} Mentor Connect. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}

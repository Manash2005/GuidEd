import React from 'react';
import Navbar from './Navbar';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-[#090E0A] text-[#F1F6F2] relative flex flex-col font-sans selection:bg-[#FFCB3D] selection:text-[#090E0A]">
      {/* Subtle organic ambient glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-[#5D9253]/10 blur-[120px]" />
        <div className="absolute top-1/4 -right-40 w-[500px] h-[500px] rounded-full bg-[#FFCB3D]/8 blur-[150px]" />
        <div className="absolute bottom-10 left-1/3 w-[450px] h-[450px] rounded-full bg-[#557945]/10 blur-[130px]" />
      </div>

      {/* Floating Header */}
      <Navbar />

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 pt-24 pb-12">
        {children}
      </main>

      {/* Clean Minimal Footer */}
      <footer className="relative z-10 border-t border-[#557945]/20 bg-[#0E1610]/80 backdrop-blur-md py-6 text-center text-xs text-[#8BA190]">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#5D9253]" />
            <span className="font-semibold text-[#F1F6F2]">GuidEd</span>
            <span className="text-[#557945]">&bull;</span>
            <span className="text-[11px] text-[#A2B5A6]">Mentorship Connect</span>
          </div>
          <div className="text-[11px] text-[#8BA190]">
            &copy; {new Date().getFullYear()} GuidEd
          </div>
        </div>
      </footer>
    </div>
  );
}

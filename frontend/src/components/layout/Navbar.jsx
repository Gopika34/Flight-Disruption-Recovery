import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Plane, ShieldAlert, Sparkles, MessageSquare, BookOpen, RotateCcw, Menu, X, PlusCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { BackendStatusPill } from './BackendStatusPill';
import { useSession } from '../../context/SessionContext';

export function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { startNewSession, sessionId } = useSession();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Overview', path: '/' },
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Assess Rights', path: '/assessment' },
    { label: 'AI Assistant', path: '/chat' },
    { label: 'DGCA Regulations', path: '/evidence' },
    { label: 'Flight Recovery', path: '/recovery' },
  ];

  const handleStartNew = () => {
    startNewSession();
    navigate('/assessment');
    setMobileMenuOpen(false);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-[#080d1a]/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-6">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 shrink-0 group">
          <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 group-hover:bg-teal-500/20 transition-colors">
            <Plane className="w-4 h-4 -rotate-45" />
          </div>
          <div className="flex flex-col">
            <span className="text-base font-extrabold tracking-tight text-white flex items-center gap-1.5">
              FlightGuard
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-teal-400 border border-slate-700 font-normal">
                DGCA AI
              </span>
            </span>
          </div>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden lg:flex items-center gap-1">
          {navLinks.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => {
                  if (item.path === '/chat') {
                    startNewSession();
                  }
                }}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                  isActive
                    ? 'text-teal-400 bg-teal-500/10 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Action Controls */}
        <div className="flex items-center gap-3 shrink-0">
          <BackendStatusPill />

          <Button
            size="sm"
            onClick={handleStartNew}
            className="hidden sm:inline-flex items-center gap-1.5"
          >
            <PlusCircle className="w-3.5 h-3.5" />
            <span>New Claim</span>
          </Button>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-b border-slate-800 bg-[#0b101b] px-4 pt-3 pb-5 space-y-2">
          {navLinks.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => {
                  if (item.path === '/chat') {
                    startNewSession();
                  }
                  setMobileMenuOpen(false);
                }}
                className={`block px-3 py-2 text-sm rounded-lg transition-colors ${
                  isActive
                    ? 'text-teal-400 bg-teal-500/10 font-semibold'
                    : 'text-slate-300 hover:text-white hover:bg-slate-800'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
          <div className="pt-3 border-t border-slate-800">
            <Button className="w-full justify-center" onClick={handleStartNew}>
              Start New Disruption Assessment
            </Button>
          </div>
        </div>
      )}
    </header>
  );
}

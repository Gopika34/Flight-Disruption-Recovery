
import React from 'react';
import { Plane, ExternalLink, ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-[#060912] text-xs text-slate-400 py-12 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">

        {/* Main Footer Grid - Always 3 Columns */}
        <div className="overflow-x-auto pb-3">
          <div className="grid grid-cols-[5fr_3fr_4fr] gap-6 min-w-[760px]">

            {/* Brand & Mission */}
            <div className="space-y-3 min-w-0">
              <Link
                to="/"
                className="flex items-center gap-2.5 text-white font-extrabold tracking-tight"
              >
                <div className="w-7 h-7 shrink-0 rounded-lg bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400">
                  <Plane className="w-3.5 h-3.5 -rotate-45" />
                </div>
                <span className="text-sm whitespace-nowrap">
                  FlightGuard Aviation Rights
                </span>
              </Link>

              <p className="text-slate-400 text-xs leading-relaxed max-w-sm">
                Deterministic statutory passenger rights and compensation
                engine grounded in DGCA Civil Aviation Requirements (CAR)
                Section 3, Series M, Part IV.
              </p>

              <div className="pt-1 flex items-center gap-2 text-[11px] font-mono text-slate-400">
                <span className="w-2 h-2 shrink-0 rounded-full bg-emerald-400 animate-pulse" />
                <span>Engine Status: Production Ready</span>
              </div>
            </div>

            {/* Platform Navigation */}
            <div className="space-y-3 min-w-0">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-200 block">
                Platform Modules
              </span>

              <ul className="space-y-2 text-xs">
                <li>
                  <Link to="/assessment" className="hover:text-teal-400 transition-colors block">
                    Disruption Assessment
                  </Link>
                </li>
                <li>
                  <Link to="/chat" className="hover:text-teal-400 transition-colors block">
                    AI Passenger Advisor
                  </Link>
                </li>
                <li>
                  <Link to="/evidence" className="hover:text-teal-400 transition-colors block">
                    DGCA Policy Clauses
                  </Link>
                </li>
                <li>
                  <Link to="/recovery" className="hover:text-teal-400 transition-colors block">
                    Live AirLabs Recovery
                  </Link>
                </li>
                <li>
                  <Link to="/dashboard" className="hover:text-teal-400 transition-colors block">
                    Passenger Dashboard
                  </Link>
                </li>
              </ul>
            </div>

            {/* Official Portals */}
            <div className="space-y-3 min-w-0">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-200 block">
                Official Regulatory Portals
              </span>

              <ul className="space-y-2 text-xs">
                <li>
                  <a
                    href="https://airsewa.gov.in"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-teal-400 transition-colors inline-flex items-start gap-1.5"
                  >
                    <span>DGCA AirSewa Grievance Portal</span>
                    <ArrowUpRight className="w-3 h-3 shrink-0 text-slate-500" />
                  </a>
                </li>

                <li>
                  <a
                    href="https://dgca.gov.in"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-teal-400 transition-colors inline-flex items-start gap-1.5"
                  >
                    <span>Directorate General of Civil Aviation (DGCA)</span>
                    <ArrowUpRight className="w-3 h-3 shrink-0 text-slate-500" />
                  </a>
                </li>

                <li>
                  <a
                    href="https://www.civilaviation.gov.in"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-teal-400 transition-colors inline-flex items-start gap-1.5"
                  >
                    <span>Ministry of Civil Aviation (MoCA)</span>
                    <ArrowUpRight className="w-3 h-3 shrink-0 text-slate-500" />
                  </a>
                </li>

                <li>
                  <a
                    href="https://flight-disruption-recovery.onrender.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-teal-400 transition-colors inline-flex items-start gap-1.5 font-mono text-[11px]"
                  >
                    <span>Backend API Server</span>
                    <ExternalLink className="w-3 h-3 shrink-0 text-slate-500" />
                  </a>
                </li>
              </ul>
            </div>

          </div>
        </div>

        {/* Bottom Legal Notice */}
        <div className="pt-6 border-t border-slate-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[11px] text-slate-500">
          <div>
            © {new Date().getFullYear()} FlightGuard. Strictly non-commercial
            evaluation tool based on official DGCA regulations. Not legal advice.
          </div>

          <div className="font-mono text-slate-500 text-[10px]">
            CAR Section 3 · Series M · Part IV Grounded
          </div>
        </div>

      </div>
    </footer>
  );
}
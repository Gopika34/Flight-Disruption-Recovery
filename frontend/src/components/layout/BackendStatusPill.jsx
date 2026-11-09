import React, { useEffect, useState } from 'react';
import { ShieldCheck, AlertCircle, RefreshCw, Cpu, Database } from 'lucide-react';
import { getReadyHealth, getLlmStatus } from '../../services/api';

export function BackendStatusPill() {
  const [readyInfo, setReadyInfo] = useState(null);
  const [llmInfo, setLlmInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const [ready, llm] = await Promise.allSettled([getReadyHealth(), getLlmStatus()]);
      if (ready.status === 'fulfilled') setReadyInfo(ready.value);
      if (llm.status === 'fulfilled') setLlmInfo(llm.value);
    } catch {
      // Ignored
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const timer = setInterval(fetchStatus, 45000); // 45s poll
    return () => clearInterval(timer);
  }, []);

  const isOperational = readyInfo?.status === 'ready';

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono border border-slate-800 bg-slate-900/90 text-slate-300 hover:text-white hover:border-slate-700 transition-colors cursor-pointer"
        title="Click to view engine diagnostic status"
      >
        <span
          className={`w-2 h-2 rounded-full ${
            isOperational ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'
          }`}
        />
        <span className="hidden sm:inline">
          {isOperational ? 'DGCA Engine Online' : 'Waking Engine...'}
        </span>
        {loading && <RefreshCw className="w-3 h-3 text-slate-500 animate-spin" />}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-72 rounded-xl border border-slate-800 bg-[#0e1626] p-4 text-xs shadow-xl z-50 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-semibold text-white">System Diagnostics</span>
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="text-slate-400 hover:text-teal-400 transition-colors flex items-center gap-1"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              <span>Ping</span>
            </button>
          </div>

          <div className="space-y-2 font-mono text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1">
                <Database className="w-3 h-3" /> MongoDB Vector:
              </span>
              <span className={readyInfo?.checks?.database === 'ok' ? 'text-emerald-400' : 'text-slate-400'}>
                {readyInfo?.checks?.database || 'checking'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Rule Evaluator:
              </span>
              <span className="text-emerald-400">Deterministic</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1">
                <Cpu className="w-3 h-3" /> Active LLM Providers:
              </span>
              <span className="text-teal-400">
                {llmInfo?.provider_count ? `${llmInfo.provider_count} Providers` : 'Configured'}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 text-[10px] text-slate-500">
            Render Service: <span className="text-slate-400">flight-disruption-recovery</span>
          </div>
        </div>
      )}
    </div>
  );
}

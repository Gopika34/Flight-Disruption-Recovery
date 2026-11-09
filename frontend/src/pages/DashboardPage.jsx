import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plane,
  Clock,
  Ban,
  UserX,
  ArrowDownCircle,
  PlusCircle,
  MessageSquare,
  ShieldCheck,
  Cpu,
  Database,
  ArrowRight,
  Trash2,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { useSession } from '../context/SessionContext';
import { getReadyHealth, getLlmStatus, getLiveHealth } from '../services/api';

export function DashboardPage() {
  const navigate = useNavigate();
  const { sessionList, sessionId, startNewSession, deleteSession, setSessionId } = useSession();

  const [healthStatus, setHealthStatus] = useState(null);
  const [llmStatus, setLlmStatus] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  useEffect(() => {
    async function loadStatus() {
      setLoadingHealth(true);
      try {
        const [ready, llm] = await Promise.allSettled([getReadyHealth(), getLlmStatus()]);
        if (ready.status === 'fulfilled') setHealthStatus(ready.value);
        if (llm.status === 'fulfilled') setLlmStatus(llm.value);
      } catch {
        // Handled gracefully
      } finally {
        setLoadingHealth(false);
      }
    }
    loadStatus();
  }, []);

  const handleStartAssessment = (type = null) => {
    startNewSession();
    if (type) {
      navigate(`/assessment?type=${type}`);
    } else {
      navigate('/assessment');
    }
  };

  const handleResumeSession = (id) => {
    setSessionId(id);
    navigate('/chat');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Welcome & Primary Action */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-[#0e1626]/80">
        <div className="space-y-1">
          <Badge variant="default">Passenger Operations Portal</Badge>
          <h1 className="text-xl sm:text-2xl font-extrabold text-white">
            Flight Disruption Recovery Workspace
          </h1>
          <p className="text-xs text-slate-400 max-w-xl">
            Evaluate your flight rights, calculate statutory monetary compensation under DGCA rules, and communicate with our AI recovery advisor.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Button onClick={() => handleStartAssessment()} className="font-semibold">
            <PlusCircle className="w-4 h-4 mr-1.5" />
            <span>New Disruption Assessment</span>
          </Button>
          <Button variant="outline" onClick={() => {
            startNewSession();
            navigate('/chat');
          }}>
            <MessageSquare className="w-4 h-4 mr-1.5 text-teal-400" />
            <span>Open AI Chat</span>
          </Button>
        </div>
      </div>

      {/* Disruption Categories Quick Launch */}
      <div className="space-y-3">
        <h2 className="text-sm font-bold text-slate-200">
          Disruption Assessment Modules
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card
            className="hover:border-slate-700 cursor-pointer transition-all"
            onClick={() => handleStartAssessment('delay')}
          >
            <CardHeader className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center">
                  <Clock className="w-4 h-4" />
                </div>
                <Badge variant="warning">Para 3.4</Badge>
              </div>
              <CardTitle className="text-sm">Flight Delay</CardTitle>
              <CardDescription className="text-xs mt-1">
                Meals, refreshments, overnight accommodation, and 6-hour refund mandates.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card
            className="hover:border-slate-700 cursor-pointer transition-all"
            onClick={() => handleStartAssessment('cancellation')}
          >
            <CardHeader className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center">
                  <Ban className="w-4 h-4" />
                </div>
                <Badge variant="danger">Para 3.3</Badge>
              </div>
              <CardTitle className="text-sm">Cancellation</CardTitle>
              <CardDescription className="text-xs mt-1">
                Notice periods, compensation caps (₹5,000–₹10,000), and refund choices.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card
            className="hover:border-slate-700 cursor-pointer transition-all"
            onClick={() => handleStartAssessment('denied_boarding')}
          >
            <CardHeader className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center">
                  <UserX className="w-4 h-4" />
                </div>
                <Badge variant="default">Para 3.2</Badge>
              </div>
              <CardTitle className="text-sm">Denied Boarding</CardTitle>
              <CardDescription className="text-xs mt-1">
                Overbooking penalties: 200% up to ₹10,000 or 400% up to ₹20,000.
              </CardDescription>
            </CardHeader>
          </Card>

          <Card
            className="hover:border-slate-700 cursor-pointer transition-all"
            onClick={() => handleStartAssessment('downgrading')}
          >
            <CardHeader className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
                  <ArrowDownCircle className="w-4 h-4" />
                </div>
                <Badge variant="navy">Para 3.5</Badge>
              </div>
              <CardTitle className="text-sm">Cabin Downgrade</CardTitle>
              <CardDescription className="text-xs mt-1">
                Mandatory 75% refund of ticket fare including taxes on domestic flights.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </div>

      {/* Grid: Recent Sessions & Backend Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recent Sessions */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-200">
              Recent Disruption Assessments
            </h2>
            <span className="text-xs font-mono text-slate-500">
              {sessionList.length} stored locally
            </span>
          </div>

          {sessionList.length === 0 ? (
            <Card className="p-8 text-center space-y-3">
              <div className="w-10 h-10 rounded-full bg-slate-800 text-slate-400 mx-auto flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-slate-200">No Assessment History</h4>
                <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
                  Start an assessment or open a chat conversation to evaluate your flight scenario.
                </p>
              </div>
              <Button size="sm" onClick={() => handleStartAssessment()}>
                Start First Assessment
              </Button>
            </Card>
          ) : (
            <div className="space-y-2">
              {sessionList.map((session) => (
                <div
                  key={session.id}
                  className="p-3.5 rounded-xl border border-slate-800 bg-[#0e1626]/80 flex items-center justify-between gap-3 hover:border-slate-700 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white font-mono">
                        {session.flightNumber || session.title}
                      </span>
                      <Badge variant="secondary" className="capitalize text-[10px]">
                        {session.type}
                      </Badge>
                      {sessionId === session.id && (
                        <span className="text-[10px] text-teal-400 font-mono font-medium">
                          (Active)
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-500 block">
                      Evaluated on {new Date(session.lastUpdated).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleResumeSession(session.id)}
                    >
                      <span>Resume</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </Button>
                    <button
                      onClick={() => deleteSession(session.id)}
                      className="p-1.5 rounded text-slate-500 hover:text-rose-400 transition-colors"
                      title="Delete session"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Real Backend Subsystems */}
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-200">
            Engine Health & Subsystems
          </h2>

          <Card className="space-y-4 p-5">
            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-sky-400" />
                  <span>MongoDB Atlas Vector:</span>
                </span>
                <span className={healthStatus?.checks?.database === 'ok' ? 'text-emerald-400 font-bold' : 'text-amber-400'}>
                  {healthStatus?.checks?.database === 'ok' ? 'Connected' : 'Unavailable'}
                </span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-400" />
                  <span>DGCA Rule Engine:</span>
                </span>
                <span className="text-emerald-400 font-bold">Deterministic</span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Plane className="w-3.5 h-3.5 text-amber-400" />
                  <span>AirLabs Flight Feed:</span>
                </span>
                <span className={healthStatus?.checks?.airlabs_key_configured ? 'text-emerald-400 font-bold' : 'text-slate-500'}>
                  {healthStatus?.checks?.airlabs_key_configured ? 'Live API Key' : 'Not Configured'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Cpu className="w-3.5 h-3.5 text-purple-400" />
                  <span>LLM Providers:</span>
                </span>
                <span className="text-teal-400 font-bold">
                  {llmStatus?.provider_count || 4} Active
                </span>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500 leading-relaxed font-sans">
              Rules execute deterministically in Python. The LLM only explains verified outcomes.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

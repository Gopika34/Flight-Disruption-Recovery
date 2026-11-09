import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Plane,
  Sparkles,
  RefreshCw,
  AlertCircle,
  HelpCircle,
  CheckCircle2,
  DollarSign,
  Utensils,
  Hotel,
  RotateCcw,
  User,
  PlusCircle,
  Bot,
  MessageSquare,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { useSession } from '../context/SessionContext';
import { streamAskAssistant, formatApiError } from '../services/api';

const PROMPT_SUGGESTIONS = [
  'My flight 6E204 was delayed by 4 hours. What are my rights?',
  'Air India cancelled my flight 12 hours before departure.',
  'I was denied boarding due to overbooking even though I checked in on time.',
  'I was downgraded from Business to Economy class on a domestic flight.',
];

const DEFAULT_WELCOME = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Hello! I am your DGCA Flight Disruption Advisor. Tell me about your flight situation (e.g. 'My flight 6E204 from Delhi to Mumbai was delayed by 4 hours' or 'My flight was cancelled with 12 hours notice'). I'll extract the facts, evaluate your legal entitlements under Indian civil aviation regulations, and guide you through your recovery options.",
  questions: [],
  entitlement: null,
  summary: [],
};

export function ChatPage() {
  const {
    sessionId,
    recordSession,
    startNewSession,
    knownFacts,
    getSessionMessages,
    saveSessionMessages,
  } = useSession();

  const [inputMessage, setInputMessage] = useState('');
  const [messages, setMessages] = useState(() => {
    if (sessionId) {
      const saved = getSessionMessages(sessionId);
      if (saved && saved.length > 0) return saved;
    }
    return [DEFAULT_WELCOME];
  });
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(null);

  const messagesContainerRef = useRef(null);
  const skipSyncRef = useRef(false);

  // When sessionId changes (e.g. user resumed a session from dashboard or clicked new conversation)
  useEffect(() => {
    // Session id was just created by our own send, so keep the live messages.
    if (skipSyncRef.current) {
      skipSyncRef.current = false;
      return;
    }
    if (sessionId) {
      const saved = getSessionMessages(sessionId);
      if (saved && saved.length > 0) {
        setMessages(saved);
        return;
      }
    }
    setMessages([DEFAULT_WELCOME]);
  }, [sessionId]);

  // Persist messages whenever updated
  useEffect(() => {
    if (sessionId && messages && messages.length > 1) {
      saveSessionMessages(sessionId, messages);
    }
  }, [messages, sessionId]);

  const scrollToBottom = () => {
    const container = messagesContainerRef.current;

    if (!container) return;

    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'auto',
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streaming]);

  const handleSendMessage = async (customText = null) => {
    const textToSend = (customText || inputMessage).trim();
    if (!textToSend || streaming) return;

    if (textToSend.length < 3) {
      setError('Please provide at least 3 characters describing your flight or situation.');
      return;
    }

    setError(null);
    setInputMessage('');

    // Append user message
    const userMsgId = crypto.randomUUID();
    const assistantMsgId = crypto.randomUUID();

    const newMessages = [
      ...messages,
      {
        id: userMsgId,
        role: 'user',
        content: textToSend,
      },
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        questions: [],
        entitlement: null,
        summary: [],
        isStreaming: true,
      },
    ];

    setMessages(newMessages);
    setStreaming(true);

    let activeSessionId = sessionId;

    await streamAskAssistant({
      message: textToSend,
      sessionId: activeSessionId,
      knownFacts: knownFacts,
      onEvent: (event) => {
        const { type, data } = event;

        if (type === 'session') {
          if (data.session_id !== sessionId) skipSyncRef.current = true;
          activeSessionId = data.session_id;
          recordSession(data.session_id, {
            title: textToSend.slice(0, 30),
          });
        } else if (type === 'question') {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    questions: [...(msg.questions || []), data.text],
                  }
                : msg
            )
          );
        } else if (type === 'result') {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    entitlement: data.entitlement,
                    summary: data.summary || [],
                  }
                : msg
            )
          );
        } else if (type === 'token') {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    content: msg.content + data.text,
                  }
                : msg
            )
          );
        } else if (type === 'done') {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    isStreaming: false,
                    status: data.status,
                  }
                : msg
            )
          );
        } else if (type === 'error') {
          const errText = formatApiError(data, 'An error occurred during evaluation.');
          setError(errText);
        }
      },
      onError: (err) => {
        const errText = formatApiError(err, 'Failed to connect to the disruption advisor engine.');
        setError(errText);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  isStreaming: false,
                  content:
                    msg.content ||
                    'I encountered an issue communicating with the engine. Please try rephrasing or sending your message again.',
                }
              : msg
          )
        );
      },
      onComplete: () => {
        setStreaming(false);
      },
    });

    setStreaming(false);
  };

  const handleStartFresh = () => {
    startNewSession();
    setError(null);
    setMessages([
      {
        id: 'welcome_new',
        role: 'assistant',
        content: 'New assessment started. Please describe what happened with your flight.',
        questions: [],
        entitlement: null,
        summary: [],
      },
    ]);
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 h-[calc(100vh-6.5rem)] min-h-[500px] flex flex-col space-y-3">
      {/* Header Bar - Note: Session ID is completely hidden from UI as requested */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white flex items-center gap-2">
              <span>FlightGuard Conversational Advisor</span>
              <Badge variant="default" className="text-[10px] py-0">
                Live Advisor
              </Badge>
            </h1>
            <span className="text-[11px] text-slate-400">
              DGCA Civil Aviation Requirements Intelligence
            </span>
          </div>
        </div>

        <Button size="sm" variant="outline" onClick={handleStartFresh} className="text-xs">
          <PlusCircle className="w-3.5 h-3.5 mr-1" />
          <span>New Conversation</span>
        </Button>
      </div>

      {/* Message Stream */}
      <div ref={messagesContainerRef} className="flex-1 min-h-0 overflow-y-auto space-y-4 pr-1">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-3 text-xs ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5" />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl p-4 space-y-3 ${
                msg.role === 'user'
                  ? 'bg-teal-600 text-slate-950 font-medium rounded-tr-sm ml-8'
                  : 'bg-[#0e1626] border border-slate-800 text-slate-100 rounded-tl-sm mr-8'
              }`}
            >
              {/* Entitlement Result Card (emitted FIRST by the backend engine) */}
              {msg.entitlement && (
                <div className="p-3.5 rounded-xl bg-slate-950 border border-teal-500/40 space-y-2 text-slate-100">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-mono text-[11px] font-bold text-teal-400 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4" />
                      <span>Statutory Entitlement Determined</span>
                    </span>
                    <Badge variant="success">DGCA CAR Compliant</Badge>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                    <div>
                      <span className="text-slate-400 text-[10px] block">Compensation</span>
                      <span className="font-mono font-bold text-white text-sm">
                        {msg.entitlement.compensation !== null
                          ? `₹${Number(msg.entitlement.compensation).toLocaleString('en-IN')}`
                          : '₹0 (Free Care Mandated)'}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400 text-[10px] block">Refund Status</span>
                      <span className="font-semibold text-emerald-400 text-xs">
                        {msg.entitlement.refund === 'full_ticket_refund'
                          ? '100% Full Ticket Refund'
                          : msg.entitlement.alt_or_refund
                          ? 'Alternate Flight or Refund'
                          : 'Continuing on Flight'}
                      </span>
                    </div>
                  </div>

                  {msg.summary && msg.summary.length > 0 && (
                    <ul className="text-[11px] text-slate-300 space-y-1 pt-2 border-t border-slate-900">
                      {msg.summary.map((s, idx) => (
                        <li key={idx} className="flex items-start gap-1.5">
                          <CheckCircle2 className="w-3 h-3 text-teal-400 shrink-0 mt-0.5" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Text Content */}
              {msg.content && (
                <div className="whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </div>
              )}

              {/* Clarification Questions from Missing Facts (Normal text, not warning) */}
              {msg.questions && msg.questions.length > 0 && (
                <div className="space-y-2 text-slate-200 text-xs leading-relaxed pt-1">
                  <p className="text-slate-100 font-medium">
                    To evaluate your exact statutory rights and compensation, please let me know:
                  </p>
                  <ul className="space-y-1.5 pl-1">
                    {msg.questions.map((q, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-slate-200">
                        <span className="text-teal-400 font-bold select-none">•</span>
                        <span>{q}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {msg.isStreaming && (
                <div className="flex items-center gap-1 text-slate-400 text-[11px]">
                  <RefreshCw className="w-3 h-3 animate-spin text-teal-400" />
                  <span>Analyzing with DGCA rules...</span>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Suggested prompts on initial screen */}
      {messages.length === 1 && (
        <div className="space-y-1.5">
          <span className="text-[11px] text-slate-400 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-teal-400" />
            <span>Try one of these real scenarios:</span>
          </span>
          <div className="flex flex-wrap gap-1.5">
            {PROMPT_SUGGESTIONS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendMessage(p)}
                className="text-[11px] px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-teal-500 transition-colors text-left"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Error alert with proper string rendering (NO [object Object]) */}
      {error && (
        <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{typeof error === 'string' ? error : formatApiError(error)}</span>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-rose-400 hover:text-rose-200 text-xs underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Input Box */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSendMessage();
        }}
        className="flex items-center gap-2 pt-2 border-t border-slate-800"
      >
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Describe your flight disruption or answer follow-up questions..."
          disabled={streaming}
          className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-teal-500 transition-colors"
        />
        <Button type="submit" disabled={streaming || !inputMessage.trim()} size="default">
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
}
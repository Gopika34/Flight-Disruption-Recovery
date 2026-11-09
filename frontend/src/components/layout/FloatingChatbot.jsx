
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Bot,
  X,
  ExternalLink,
  Send,
  RefreshCw,
} from 'lucide-react';

import { Button } from '../ui/button';
import { useSession } from '../../context/SessionContext';

const DEFAULT_WELCOME = {
  id: 'welcome',
  role: 'assistant',
  content:
    "Hello! I am your DGCA Flight Disruption Advisor. Tell me about your flight situation (e.g., 'My flight 6E204 was delayed by 4 hours'). I'll evaluate your rights under DGCA regulations.",
  questions: [],
  entitlement: null,
  summary: [],
};

export function FloatingChatbot() {
  const location = useLocation();
  const navigate = useNavigate();

  const {
    sessionId,
    startNewSession,
    saveSessionMessages,
  } = useSession();

  const [scrolledBeyondHero, setScrolledBeyondHero] = useState(
    () => typeof window !== 'undefined' && window.scrollY > 280
  );

  const [chatModalOpen, setChatModalOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([DEFAULT_WELCOME]);
  const [chatInput, setChatInput] = useState('');
  const [chatStreaming, setChatStreaming] = useState(false);
  const [chatError, setChatError] = useState(null);

  const isLandingPage = location.pathname === '/';
  const isChatPage = location.pathname === '/chat';

  // Track scrolling only on the landing page.
  useEffect(() => {
    if (!isLandingPage) {
      setScrolledBeyondHero(false);
      return;
    }

    const handleScroll = () => {
      setScrolledBeyondHero(window.scrollY > 280);
    };

    handleScroll();

    window.addEventListener('scroll', handleScroll, {
      passive: true,
    });

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, [isLandingPage]);

  // Hide the floating chatbot on the dedicated chat page.
  if (isChatPage) {
    return null;
  }

  // Hide it on the landing page until the user scrolls.
  if (isLandingPage && !scrolledBeyondHero) {
    return null;
  }

  const handleOpenChat = () => {
    startNewSession();
    setChatMessages([DEFAULT_WELCOME]);
    setChatInput('');
    setChatError(null);
    setChatModalOpen(true);
  };

  const handleOpenFullscreen = () => {
    if (sessionId && chatMessages.length > 1) {
      saveSessionMessages(sessionId, chatMessages);
    }

    navigate('/chat');
  };

  // Connect your original streaming API implementation here.
  const handleSendFloatingChat = async () => {
    if (!chatInput.trim() || chatStreaming) return;

    // Preserve your original handleSendFloatingChat implementation here.
    // This placeholder intentionally does not send a fake API request.
    setChatError(
      'Connect your existing floating chat API handler here.'
    );
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!chatModalOpen ? (
        <button
          onClick={handleOpenChat}
          className="group relative flex items-center gap-2.5 px-4 py-3 rounded-full bg-teal-600 hover:bg-teal-500 text-slate-950 font-bold shadow-2xl transition-all hover:scale-105 cursor-pointer border border-teal-400/40"
          title="Open AI Flight Advisor"
        >
          <div className="w-7 h-7 rounded-full bg-slate-950/20 flex items-center justify-center">
            <Bot className="w-4 h-4" />
          </div>

          <span className="text-xs tracking-wide">
            Chat with AI Advisor
          </span>

          <span className="absolute top-0 right-0 -mt-1 -mr-1 w-2.5 h-2.5 rounded-full bg-emerald-300 animate-ping" />
        </button>
      ) : (
        <div className="w-[94vw] sm:w-[400px] h-[480px] sm:h-[520px] max-h-[82vh] bg-[#0c1424] border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300">

          {/* Header */}
          <div className="px-4 py-3.5 bg-[#080d1a] border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center">
                <Bot className="w-3.5 h-3.5" />
              </div>

              <div>
                <h3 className="text-xs font-bold text-white">
                  FlightGuard AI Advisor
                </h3>
                <span className="text-[10px] text-teal-400 font-mono">
                  DGCA CAR Intelligence
                </span>
              </div>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={handleOpenFullscreen}
                className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 text-[11px] flex items-center gap-1"
                title="Open Fullscreen Chat"
              >
                <ExternalLink className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => setChatModalOpen(false)}
                className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
                title="Close Chat"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Message Feed */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3 text-xs">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2.5 ${
                  msg.role === 'user'
                    ? 'justify-end'
                    : 'justify-start'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-6 h-6 rounded-md bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center shrink-0 mt-0.5">
                    <Bot className="w-3 h-3" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] rounded-xl p-3 space-y-2 ${
                    msg.role === 'user'
                      ? 'bg-teal-600 text-slate-950 font-medium rounded-tr-sm ml-6'
                      : 'bg-[#121c31] border border-slate-800 text-slate-100 rounded-tl-sm mr-6'
                  }`}
                >
                  {msg.entitlement && (
                    <div className="p-2.5 rounded-lg bg-slate-950 border border-teal-500/30 space-y-1">
                      <span className="font-mono text-[10px] font-bold text-teal-400 block">
                        Entitlement Determined:
                      </span>

                      <span className="font-mono font-bold text-white text-xs">
                        {msg.entitlement.compensation !== null
                          ? `₹${Number(
                              msg.entitlement.compensation
                            ).toLocaleString('en-IN')} Cash`
                          : 'Free Duty of Care'}
                      </span>
                    </div>
                  )}

                  {msg.content && (
                    <div className="whitespace-pre-wrap leading-relaxed">
                      {msg.content}
                    </div>
                  )}

                  {msg.questions?.length > 0 && (
                    <div className="space-y-1.5 text-slate-200 text-[11px] pt-1">
                      <p className="font-medium text-slate-100">
                        Please let me know:
                      </p>

                      <ul className="space-y-1 pl-1">
                        {msg.questions.map((q, idx) => (
                          <li
                            key={idx}
                            className="flex items-start gap-1.5"
                          >
                            <span className="text-teal-400 font-bold">
                              •
                            </span>
                            <span>{q}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {msg.isStreaming && (
                    <div className="flex items-center gap-1 text-slate-400 text-[10px]">
                      <RefreshCw className="w-3 h-3 animate-spin text-teal-400" />
                      <span>Thinking...</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Error Banner */}
          {chatError && (
            <div className="px-3 py-2 bg-rose-500/10 border-t border-rose-500/20 text-rose-300 text-[11px] flex items-center justify-between">
              <span>{chatError}</span>

              <button
                onClick={() => setChatError(null)}
                className="underline"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendFloatingChat();
            }}
            className="p-3 bg-[#080d1a] border-t border-slate-800 flex items-center gap-2"
          >
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Describe your flight situation..."
              className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500"
            />

            <Button
              type="submit"
              size="sm"
              disabled={chatStreaming || !chatInput.trim()}
              className="h-8 px-3"
            >
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
        </div>
      )}
    </div>
  );
}

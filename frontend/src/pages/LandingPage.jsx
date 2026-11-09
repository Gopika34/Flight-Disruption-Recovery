
import { useNavigate } from 'react-router-dom';
import {
  Clock,
  Ban,
  UserX,
  ArrowDownCircle,
  ShieldCheck,
  Scale,
  Cpu,
  ArrowRight,
  Database,
  Plane,
  Sparkles,
} from 'lucide-react';

import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { SpotlightCard } from '../components/reactbits/SpotlightCard';
import { BlurText } from '../components/reactbits/BlurText';
import { Aurora } from '../components/reactbits/Aurora';
import { useSession } from '../context/SessionContext';

export function LandingPage() {
  const navigate = useNavigate();
  const { startNewSession } = useSession();

  const handleStartAssessment = (type = null) => {
    startNewSession();

    if (type) {
      navigate(`/assessment?type=${type}`);
    } else {
      navigate('/assessment');
    }
  };

  const disruptionTypes = [
    {
      id: 'delay',
      title: 'Flight Delays',
      description:
        'Statutory meals after 2h, 3h, or 4h based on block time. Mandatory overnight hotel accommodation and 6-hour full refund option.',
      rule: 'DGCA CAR Para 3.4',
      badge: 'Up to 100% Refund + Care',
      icon: Clock,
      color: 'text-amber-400',
    },
    {
      id: 'cancellation',
      title: 'Flight Cancellations',
      description:
        'Mandatory monetary compensation up to ₹10,000 for notice under 24 hours, plus full ticket refund or alternate flight accommodations.',
      rule: 'DGCA CAR Para 3.3',
      badge: '₹5,000 to ₹10,000 Cap',
      icon: Ban,
      color: 'text-rose-400',
    },
    {
      id: 'denied_boarding',
      title: 'Denied Boarding (Overbooking)',
      description:
        'Involuntary boarding denial guarantees 200% up to ₹10,000 or 400% up to ₹20,000 plus full ticket refund if alternate flight is declined.',
      rule: 'DGCA CAR Para 3.2',
      badge: '200% - 400% Basic Fare',
      icon: UserX,
      color: 'text-teal-400',
    },
    {
      id: 'downgrading',
      title: 'Involuntary Downgrading',
      description:
        'Statutory 75% refund of total ticket amount including taxes on domestic flights, or 30% to 75% on international routes.',
      rule: 'DGCA CAR Para 3.5',
      badge: '75% Fare + Tax Refund',
      icon: ArrowDownCircle,
      color: 'text-sky-400',
    },
  ];

  return (
    <div className="relative min-h-screen flex flex-col overflow-hidden">
      {/* Aurora Ambient Atmosphere */}
      <Aurora />

      {/* Hero Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-20 lg:pt-24 lg:pb-28 text-center space-y-6">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-teal-500/30 bg-teal-500/10 text-teal-300 text-xs font-mono font-medium tracking-wide">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Official DGCA CAR Section 3 Series M Part IV Grounding</span>
        </div>

        <div className="max-w-4xl mx-auto space-y-4">
          <BlurText
            text="When flights go wrong, know what comes next."
            className="text-3xl sm:text-5xl lg:text-6xl text-white font-extrabold leading-tight text-center"
            delay={60}
          />

          <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto leading-relaxed">
            Intelligent flight disruption recovery. We combine deterministic
            regulatory policy rules with vector retrieval to assess your rights,
            calculate exact statutory compensation, and explore live flight
            options.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
          <Button
            size="lg"
            onClick={() => handleStartAssessment()}
            className="w-full sm:w-auto px-6 py-3 font-bold"
          >
            <span>Check My Flight Rights</span>
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>

          <Button
            size="lg"
            variant="outline"
            onClick={() => {
              startNewSession();
              navigate('/chat');
            }}
            className="w-full sm:w-auto px-6 py-3"
          >
            <Sparkles className="w-4 h-4 mr-2 text-teal-400" />
            <span>Chat with AI Advisor</span>
          </Button>
        </div>

        {/* Quick Highlights Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 max-w-4xl mx-auto pt-10 text-left">
          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
            <span className="text-[11px] text-slate-400 font-mono block">
              Statutory Precision
            </span>
            <span className="text-sm font-bold text-white font-mono">
              100% Deterministic
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
            <span className="text-[11px] text-slate-400 font-mono block">
              RAG Vector Grounding
            </span>
            <span className="text-sm font-bold text-teal-400 font-mono">
              MongoDB Atlas
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
            <span className="text-[11px] text-slate-400 font-mono block">
              Flight Feed Stream
            </span>
            <span className="text-sm font-bold text-white font-mono">
              Live AirLabs API
            </span>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
            <span className="text-[11px] text-slate-400 font-mono block">
              Multi-Turn Memory
            </span>
            <span className="text-sm font-bold text-teal-400 font-mono">
              Persistent Sessions
            </span>
          </div>
        </div>
      </section>

      {/* Disruption Categories */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-2">
          <Badge variant="navy">Disruption Coverage</Badge>

          <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
            Four Regulated Passenger Protections
          </h2>

          <p className="text-sm text-slate-400">
            Indian aviation guidelines mandate concrete rights depending on the
            exact event.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {disruptionTypes.map((item) => {
            const Icon = item.icon;

            return (
              <SpotlightCard
                key={item.id}
                className="flex flex-col justify-between hover:border-slate-700 cursor-pointer group"
                onClick={() => handleStartAssessment(item.id)}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-lg bg-slate-800/80 border border-slate-700/80 flex items-center justify-center">
                      <Icon className={`w-5 h-5 ${item.color}`} />
                    </div>

                    <span className="text-[11px] font-mono text-slate-400">
                      {item.rule}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white group-hover:text-teal-400 transition-colors">
                      {item.title}
                    </h3>

                    <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>

                <div className="pt-5 mt-5 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-xs font-mono text-teal-400 font-medium">
                    {item.badge}
                  </span>

                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-teal-400 group-hover:translate-x-1 transition-all" />
                </div>
              </SpotlightCard>
            );
          })}
        </div>
      </section>

      {/* 3-Step Process */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center max-w-2xl mx-auto mb-12 space-y-2">
          <Badge variant="secondary">Resolution Flow</Badge>

          <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
            Three Steps from Disruption to Resolution
          </h2>

          <p className="text-sm text-slate-400">
            A guided experience that detects missing information and provides
            exact legal answers.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-xl border border-slate-800 bg-[#0c1424] space-y-3">
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 font-mono font-bold flex items-center justify-center text-sm border border-teal-500/20">
              01
            </div>

            <h3 className="text-base font-bold text-white">
              1. Tell us what happened
            </h3>

            <p className="text-xs text-slate-400 leading-relaxed">
              Provide your flight number, date, and disruption type. Use our
              structured form or talk naturally with our streaming AI assistant.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-800 bg-[#0c1424] space-y-3">
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 font-mono font-bold flex items-center justify-center text-sm border border-teal-500/20">
              02
            </div>

            <h3 className="text-base font-bold text-white">
              2. Deterministic Rule Evaluation
            </h3>

            <p className="text-xs text-slate-400 leading-relaxed">
              Your scenario is evaluated directly against DGCA CAR regulations
              in Python. The LLM only explains the verdict—it never hallucinates
              amounts.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-800 bg-[#0c1424] space-y-3">
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 font-mono font-bold flex items-center justify-center text-sm border border-teal-500/20">
              03
            </div>

            <h3 className="text-base font-bold text-white">
              3. Review Recovery Options
            </h3>

            <p className="text-xs text-slate-400 leading-relaxed">
              Examine live AirLabs alternative flights, hotel and meal
              obligations, and generate a formal passenger rights claim notice.
            </p>
          </div>
        </div>
      </section>

      {/* Technology & Trust Section */}
      <section className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="p-8 lg:p-10 rounded-2xl border border-slate-800 bg-gradient-to-br from-[#0c1424] to-[#070b14] space-y-6">
          <div className="max-w-2xl space-y-2">
            <Badge variant="default">Aviation Architecture</Badge>

            <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
              Why Deterministic Grounding Matters
            </h2>

            <p className="text-xs text-slate-400 leading-relaxed">
              General purpose LLMs frequently hallucinate legal figures and
              misapply airline exemptions. FlightGuard solves this through an
              architectural boundary:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-4">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
              <Scale className="w-5 h-5 text-teal-400" />

              <h4 className="text-sm font-bold text-white">
                The Rule Engine Decides
              </h4>

              <p className="text-xs text-slate-400 leading-relaxed">
                Eligibility and compensation figures are computed strictly by
                Python decision trees encoding DGCA CAR Series M Part IV.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
              <Database className="w-5 h-5 text-sky-400" />

              <h4 className="text-sm font-bold text-white">
                Vector Evidence Retrieval
              </h4>

              <p className="text-xs text-slate-400 leading-relaxed">
                MongoDB Atlas vector search retrieves the exact legal clauses
                and official paragraph texts to substantiate every finding.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
              <Cpu className="w-5 h-5 text-purple-400" />

              <h4 className="text-sm font-bold text-white">
                Grounded Explanation
              </h4>

              <p className="text-xs text-slate-400 leading-relaxed">
                The language model only explains the calculated decision in
                clear, compassionate prose. It cannot alter the legal outcome.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

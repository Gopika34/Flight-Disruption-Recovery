import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { AlertCircle, CheckCircle2, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { DisruptionForm } from '../components/assessment/DisruptionForm';
import { ScenarioPresets } from '../components/assessment/ScenarioPresets';
import { generateRecoveryPlan } from '../services/api';
import { useSession } from '../context/SessionContext';

export function AssessmentPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { sessionId, setSessionId, recordSession, setActivePlan, setKnownFacts } = useSession();

  const preselectedType = searchParams.get('type') || 'delay';

  const [formData, setFormData] = useState({
    type: preselectedType,
    origin: 'DEL',
    destination: 'BOM',
    flight_number: '6E204',
    scheduled_departure: '21:00',
    delay_minutes: 240,
    total_delay_from_published_minutes: 240,
    block_time_minutes: 130,
    checked_in_on_time: true,
    domestic: true,
    reason: 'operational',
    notice_hours: 12,
    has_contact_info: true,
    alternate_flight_offered: false,
    basic_fare: 4500,
    fuel_charge: 1200,
    confirmed_booking: true,
    voluntary_surrender: false,
    overbooking: true,
    sector: 'domestic',
    ticket_amount_including_taxes: 12000,
    involuntary: true,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [missingFacts, setMissingFacts] = useState([]);

  useEffect(() => {
    if (searchParams.get('type')) {
      setFormData((prev) => ({ ...prev, type: searchParams.get('type') }));
    }
  }, [searchParams]);

  const handlePresetSelect = (presetPayload) => {
    setFormData((prev) => ({
      ...prev,
      ...presetPayload,
    }));
    setError(null);
    setMissingFacts([]);
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setMissingFacts([]);

    try {
      const plan = await generateRecoveryPlan(formData);
      setActivePlan(plan);
      setKnownFacts(formData);

      // Record session in history
      const newSessionId = sessionId || crypto.randomUUID();
      recordSession(newSessionId, {
        flight_number: formData.flight_number,
        type: formData.type,
        status: plan.decision?.status || 'completed',
        summary: plan.decision?.notes?.[0] || 'Disruption rights evaluated',
      });

      if (plan.decision?.status === 'needs_more_info') {
        setMissingFacts(plan.decision.missing_facts || []);
        setError('The engine requires additional facts to complete the statutory determination.');
      } else {
        // Successfully resolved
        navigate('/results');
      }
    } catch (err) {
      setError(err.message || 'Failed to evaluate disruption scenario.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-xl sm:text-2xl font-extrabold text-white">
          Disruption Assessment Workspace
        </h1>
        <p className="text-xs text-slate-400">
          Enter flight and disruption facts to evaluate statutory compensation, care obligations, and refund eligibility against DGCA CAR Section 3.
        </p>
      </div>

      {/* Scenario Presets Bar */}
      <ScenarioPresets onSelectPreset={handlePresetSelect} />

      {/* Error / Missing Facts Notice */}
      {error && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start gap-3">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <strong className="block font-semibold">Evaluation Notice:</strong>
            <p>{error}</p>
            {missingFacts.length > 0 && (
              <p className="text-[11px] text-amber-200">
                Please complete the highlighted inputs ({missingFacts.join(', ')}) below and click Evaluate again.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Main Form */}
      <DisruptionForm
        formData={formData}
        setFormData={setFormData}
        onSubmit={handleSubmit}
        loading={loading}
        missingFacts={missingFacts}
      />
    </div>
  );
}

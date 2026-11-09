import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Utensils,
  Hotel,
  RotateCcw,
  Scale,
  Printer,
  Copy,
  Check,
  ArrowRight,
  Plane,
  FileText,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Info,
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';
import { CountUp } from '../components/reactbits/CountUp';
import { useSession } from '../context/SessionContext';

export function ResultsPage() {
  const navigate = useNavigate();
  const { activePlan, knownFacts } = useSession();
  const [copied, setCopied] = useState(false);
  const [passengerName, setPassengerName] = useState('Passenger');
  const [pnr, setPnr] = useState('ABC123');

  if (!activePlan || !activePlan.decision) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-slate-800 text-slate-400 mx-auto flex items-center justify-center">
          <FileText className="w-6 h-6" />
        </div>
        <h2 className="text-base font-bold text-white">No Disruption Evaluation Found</h2>
        <p className="text-xs text-slate-400 max-w-sm mx-auto">
          Please run an assessment or consult the AI advisor to determine your legal entitlements under DGCA passenger rights.
        </p>
        <Button onClick={() => navigate('/assessment')}>
          Start Flight Assessment
        </Button>
      </div>
    );
  }

  const { decision, alternatives = [], stay, clauses = [], flight_info } = activePlan;

  // Determine clear statutory outcomes
  const isDelay = decision.type === 'delay';
  const isCancellation = decision.type === 'cancellation';
  const isDeniedBoarding = decision.type === 'denied_boarding';
  const isDowngrade = decision.type === 'downgrading';
  const delayMinutes = Number(knownFacts?.delay_minutes || 0);

  // Compensation evaluation
  let compensationDisplay = '';
  let compensationSubtext = '';
  let isCashEligible = false;

  if (decision.compensation !== null && decision.compensation > 0) {
    isCashEligible = true;
    compensationDisplay = `₹${Number(decision.compensation).toLocaleString('en-IN')}`;
    compensationSubtext =
      isCancellation
        ? 'Statutory cash compensation under DGCA Para 3.3.2 for cancellation with <24h notice.'
        : isDeniedBoarding
        ? 'Statutory compensation under DGCA Para 3.2.2 (200%–400% basic fare + fuel charge).'
        : isDowngrade
        ? 'Mandatory 75% refund of ticket fare including taxes under DGCA Para 3.5.1.'
        : 'Statutory cash entitlement.';
  } else if (isDelay) {
    isCashEligible = false;
    compensationDisplay = '₹0 Cash';
    compensationSubtext =
      'Under DGCA CAR Section 3 Series M Part IV, flight delays do NOT entitle passengers to direct cash compensation (which is reserved for cancellations & denied boarding). Instead, your entitlement is 100% Free Duty of Care (Meals & Overnight Hotel Stay).';
  } else if (decision.status === 'needs_more_info') {
    compensationDisplay = 'Pending Missing Facts';
    compensationSubtext =
      'Please supply the remaining flight details (e.g. basic fare, fuel charge, or notice hours) to calculate the exact figure.';
  } else {
    compensationDisplay = '₹0 Cash';
    compensationSubtext =
      'No cash penalty applies because the airline either provided acceptable alternative travel or advance notice exceeding statutory thresholds.';
  }

  // Refund evaluation
  let refundStatus = '';
  let refundSubtext = '';

  if (decision.refund === 'full_ticket_refund') {
    refundStatus = '100% Full Ticket Refund';
    refundSubtext =
      'You are legally entitled to receive a full cash refund of your ticket price including all taxes and fees, with zero cancellation charges.';
  } else if (isDelay && delayMinutes >= 360) {
    refundStatus = '100% Full Refund Option (Delay ≥ 6h)';
    refundSubtext =
      'Under DGCA Para 3.4.2, when a domestic flight is delayed 6 hours or more, you have the legal right to cancel and claim a 100% immediate full refund or take an alternative flight.';
  } else if (isDelay && delayMinutes < 360) {
    refundStatus = 'Continuing Flight (Full Refund at 6h+)';
    refundSubtext =
      `Your flight is delayed by ${Math.floor(delayMinutes / 60)}h ${delayMinutes % 60}m. If the airline further delays departure past 6 hours, you immediately become entitled to a 100% full ticket refund under Para 3.4.2.`;
  } else if (decision.alt_or_refund) {
    refundStatus = 'Alternate Flight or Full Refund Choice';
    refundSubtext =
      'Under DGCA regulations, you have the sovereign choice between taking an alternate rebooked flight or claiming a full ticket refund.';
  } else {
    refundStatus = 'Standard Booking Active';
    refundSubtext =
      'The current disruption duration does not meet the mandatory full refund threshold under DGCA rules.';
  }

  const claimNoticeText = `STATUTORY PASSENGER COMPENSATION & GRIEVANCE CLAIM
Pursuant to DGCA Civil Aviation Requirements (CAR) Section 3, Series M, Part IV

Date: ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
To: The Nodal Officer / Customer Grievance Cell,
Operating Airline: ${knownFacts?.flight_number ? knownFacts.flight_number.slice(0, 2) : 'Airline'}

Passenger Name: ${passengerName}
Booking PNR: ${pnr}
Flight Number: ${knownFacts?.flight_number || 'N/A'}
Sector: ${knownFacts?.origin || 'DEL'} to ${knownFacts?.destination || 'BOM'}
Scheduled Departure: ${knownFacts?.scheduled_departure || 'N/A'}
Disruption Event: ${decision.type?.toUpperCase()}

STATUTORY FINDINGS & ENTITLEMENTS:
1. Financial Compensation: ${isCashEligible ? compensationDisplay : 'Not statutory for this delay tier (Duty of Care applies)'}
2. Ticket Refund Entitlement: ${refundStatus}
3. Care & Facilities Mandate:
   - Meals & Refreshments: ${decision.meals ? 'Mandatory under Para 3.8.1 (a)' : 'Not Triggered'}
   - Hotel Accommodation & Transfers: ${decision.hotel || stay?.owed_by_airline ? 'Mandatory under Para 3.4.3 / 3.8.1 (b)' : 'Not Triggered'}

APPLICABLE DGCA REGULATORY PARAGRAPHS:
${decision.clauses?.map((c) => `Para ${c}`).join(', ')}

Please process this statutory claim and acknowledge receipt within regulatory timeframes.`;

  const handleCopyNotice = () => {
    navigator.clipboard.writeText(claimNoticeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const [scriptCopied, setScriptCopied] = useState(false);
  const [evidenceChecked, setEvidenceChecked] = useState({
    cert: false,
    fids: false,
    boarding: false,
    bills: false,
  });

  const airportScript = isCancellation
    ? `Hello, my flight ${knownFacts?.flight_number || ''} was cancelled. Under DGCA CAR Section 3, Series M, Part IV, Para 3.3.2, because cancellation was notified with less than 24 hours notice, I am legally entitled to statutory financial compensation of ${compensationDisplay} and either an alternate flight or full ticket refund. Please provide my written cancellation endorsement and process this claim.`
    : isDeniedBoarding
    ? `I have a confirmed booking and checked in on time for flight ${knownFacts?.flight_number || ''}. Under DGCA CAR Section 3, Series M, Part IV, Para 3.2.2, denying boarding due to overbooking requires statutory financial compensation of ${compensationDisplay} plus alternate travel or refund. Please call the Duty Manager to issue my compensation slip.`
    : `Hello, my flight ${knownFacts?.flight_number || ''} is delayed by ${Math.floor(delayMinutes / 60)}h ${delayMinutes % 60}m. Under DGCA Civil Aviation Requirements Section 3, Series M, Part IV, Para 3.8.1 (a), airlines are legally required to provide free meals and refreshments during waiting time. Please provide my meal vouchers now.${decision.hotel || stay?.owed_by_airline ? ' Additionally, under Para 3.4.3, as this delay extends overnight, complimentary hotel accommodation and airport transfers are mandatory.' : ''}`;

  const handleCopyScript = () => {
    navigator.clipboard.writeText(airportScript);
    setScriptCopied(true);
    setTimeout(() => setScriptCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl border border-slate-800 bg-[#0e1626]">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="capitalize text-xs font-mono">
              {decision.type?.replace('_', ' ')}
            </Badge>
            <Badge variant={isCashEligible ? 'success' : 'default'}>
              {isCashEligible ? 'Eligible for Cash Payout' : 'Duty of Care Active'}
            </Badge>
          </div>
          <h1 className="text-lg sm:text-xl font-extrabold text-white">
            Official DGCA Passenger Entitlement Determination
          </h1>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button size="sm" variant="outline" onClick={handleCopyNotice}>
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Claim Copied' : 'Copy Grievance Notice'}</span>
          </Button>
          <Button size="sm" onClick={handlePrint}>
            <Printer className="w-3.5 h-3.5" />
            <span>Print Claim Notice</span>
          </Button>
        </div>
      </div>

      {/* Prominent Statutory Verdict Banner */}
      <div
        className={`p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
          isCashEligible
            ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
            : isDelay
            ? 'bg-teal-950/40 border-teal-500/40 text-teal-200'
            : 'bg-slate-900 border-slate-800 text-slate-200'
        }`}
      >
        <div className="flex items-start gap-3">
          <div
            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
              isCashEligible ? 'bg-emerald-500/20 text-emerald-400' : 'bg-teal-500/20 text-teal-400'
            }`}
          >
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white flex flex-wrap items-center gap-2">
              <span>
                {isCashEligible
                  ? `Statutory Verdict: Eligible for ${compensationDisplay} Direct Cash`
                  : isDelay
                  ? 'Statutory Verdict: Mandatory Duty of Care (Delays Do Not Pay Direct Cash)'
                  : isDowngrade
                  ? 'Statutory Verdict: Eligible for 75% Ticket Fare Refund'
                  : 'Statutory Verdict: Finalized Under DGCA CAR Section 3'}
              </span>
            </h2>
            <p className="text-xs text-slate-300 mt-1 leading-relaxed">
              {isCashEligible
                ? `You have a valid statutory claim under DGCA CAR Section 3, Series M, Part IV. The airline must pay you ${compensationDisplay} and provide a full ticket refund or alternate rebooking.`
                : isDelay
                ? 'Under Indian DGCA regulations, flight delays do NOT qualify for direct cash compensation (cash compensation is only for cancellations and denied boarding). Instead, the airline is legally required to provide free meals, refreshments, and hotel accommodation right now.'
                : 'Your entitlement has been evaluated deterministically against DGCA Civil Aviation Requirements.'}
            </p>
          </div>
        </div>
      </div>

      {/* 3 Core Result Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Statutory Compensation Card */}
        <Card className="p-5 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400 font-medium">Statutory Cash Compensation</span>
              <Badge variant={isCashEligible ? 'success' : 'secondary'} className="text-[10px]">
                {isCashEligible ? 'Cash Owed' : 'No Direct Cash'}
              </Badge>
            </div>
            <div className="text-2xl font-extrabold text-white">
              {isCashEligible ? (
                <span className="text-teal-400 font-mono">{compensationDisplay}</span>
              ) : (
                <span className="text-slate-300 font-mono text-xl">{compensationDisplay}</span>
              )}
            </div>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed pt-3 border-t border-slate-850">
            {compensationSubtext}
          </p>
        </Card>

        {/* Ticket Refund Card */}
        <Card className="p-5 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400 font-medium">Ticket Refund Rights</span>
              <Badge variant={decision.refund === 'full_ticket_refund' || (isDelay && delayMinutes >= 360) ? 'success' : 'secondary'} className="text-[10px]">
                {decision.refund === 'full_ticket_refund' || (isDelay && delayMinutes >= 360) ? '100% Refund' : 'Conditional'}
              </Badge>
            </div>
            <div className="text-base font-bold text-white leading-snug">
              {refundStatus}
            </div>
          </div>
          <p className="text-[11px] text-slate-400 leading-relaxed pt-3 border-t border-slate-850">
            {refundSubtext}
          </p>
        </Card>

        {/* Live Alternatives Card */}
        <Card className="p-5 flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-slate-400 font-medium">Alternative Flights Available</span>
              <Badge variant="navy" className="text-[10px]">AirLabs Feed</Badge>
            </div>
            <div className="text-2xl font-extrabold text-white font-mono flex items-baseline gap-1.5">
              <span className="text-teal-400">{alternatives.length}</span>
              <span className="text-xs text-slate-400 font-normal">Flights In Window</span>
            </div>
          </div>
          <Link
            to="/recovery"
            className="text-xs text-teal-400 hover:underline flex items-center gap-1 pt-3 border-t border-slate-850"
          >
            <span>Browse Flights & Rebooking</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </Card>
      </div>

      {/* ACTION GUIDE: What You Need to Do Now */}
      <Card className="p-6 border-teal-500/30 bg-gradient-to-br from-[#0c1626] to-[#070b14] space-y-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">
                What You Need to Do Right Now (Step-by-Step Action Plan)
              </h2>
              <p className="text-xs text-slate-400">
                Actionable instructions to enforce your statutory rights with airline ground staff and regulatory bodies.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Step 1: Airport Counter */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <span className="font-mono text-teal-400 font-bold text-xs block">
                Step 1: At the Airport Counter
              </span>
              <p className="text-slate-300 leading-relaxed text-[11px]">
                {decision.meals
                  ? 'Approach the airline customer service counter. Show staff this verbatim regulatory script demanding immediate food vouchers under DGCA Para 3.8.1 (a).'
                  : 'Check in on time and monitor departure display boards at your gate.'}
                {decision.hotel || stay?.owed_by_airline
                  ? ' Because your delay extends overnight or exceeds 6 hours at night, demand complimentary hotel accommodation and taxi transfers citing Para 3.4.3.'
                  : ''}
              </p>
            </div>

            <div className="pt-2 border-t border-slate-800 space-y-2">
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-850 text-[11px] text-slate-300 italic font-sans leading-relaxed">
                "{airportScript.slice(0, 140)}..."
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCopyScript}
                className="w-full text-[11px] h-7"
              >
                {scriptCopied ? <Check className="w-3 h-3 text-emerald-400 mr-1" /> : <Copy className="w-3 h-3 mr-1" />}
                <span>{scriptCopied ? 'Script Copied!' : 'Copy Script for Staff'}</span>
              </Button>
            </div>
          </div>

          {/* Step 2: Documentation */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <span className="font-mono text-teal-400 font-bold text-xs block">
              Step 2: Collect Required Proof
            </span>
            <p className="text-slate-400 text-[11px]">
              Airlines often dispute delays later. Collect these before leaving the airport:
            </p>
            <div className="space-y-2 text-[11px] text-slate-300">
              <label className="flex items-start gap-2 cursor-pointer hover:text-white">
                <input
                  type="checkbox"
                  checked={evidenceChecked.cert}
                  onChange={(e) => setEvidenceChecked((prev) => ({ ...prev, cert: e.target.checked }))}
                  className="rounded border-slate-700 bg-slate-950 text-teal-500 mt-0.5"
                />
                <span>Written delay certificate with airline stamp and reason.</span>
              </label>

              <label className="flex items-start gap-2 cursor-pointer hover:text-white">
                <input
                  type="checkbox"
                  checked={evidenceChecked.fids}
                  onChange={(e) => setEvidenceChecked((prev) => ({ ...prev, fids: e.target.checked }))}
                  className="rounded border-slate-700 bg-slate-950 text-teal-500 mt-0.5"
                />
                <span>Photos of airport FIDS departure screens showing delay time.</span>
              </label>

              <label className="flex items-start gap-2 cursor-pointer hover:text-white">
                <input
                  type="checkbox"
                  checked={evidenceChecked.boarding}
                  onChange={(e) => setEvidenceChecked((prev) => ({ ...prev, boarding: e.target.checked }))}
                  className="rounded border-slate-700 bg-slate-950 text-teal-500 mt-0.5"
                />
                <span>Boarding pass, bag tags, and airline SMS notices.</span>
              </label>

              <label className="flex items-start gap-2 cursor-pointer hover:text-white">
                <input
                  type="checkbox"
                  checked={evidenceChecked.bills}
                  onChange={(e) => setEvidenceChecked((prev) => ({ ...prev, bills: e.target.checked }))}
                  className="rounded border-slate-700 bg-slate-950 text-teal-500 mt-0.5"
                />
                <span>Receipts for any food, water, or hotel paid from your own pocket.</span>
              </label>
            </div>
          </div>

          {/* Step 3: Formal Claim / AirSewa */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 flex flex-col justify-between">
            <div className="space-y-2">
              <span className="font-mono text-teal-400 font-bold text-xs block">
                Step 3: Submit Grievance & Escalate
              </span>
              <p className="text-slate-300 leading-relaxed text-[11px]">
                {isCashEligible
                  ? `Copy the generated Grievance Notice below and email it to the airline's Nodal Officer for payment of ${compensationDisplay}. Airlines have 30 days to resolve statutory claims.`
                  : 'If the airline refuses to provide mandatory meals or hotel stay, save all food/hotel receipts. Submit an official reimbursement claim below.'}
              </p>
              <p className="text-slate-400 text-[11px]">
                If the airline ignores your claim or takes longer than 30 days, escalate directly to the Ministry of Civil Aviation AirSewa portal for binding regulatory action.
              </p>
            </div>

            <a
              href="https://airsewa.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-teal-500/10 border border-teal-500/30 text-teal-300 hover:bg-teal-500/20 text-xs font-semibold transition-colors"
            >
              <span>Escalate to DGCA AirSewa</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </Card>

      {/* Care & Facilities 3-Column Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Meals */}
        <div className="p-4 rounded-xl border border-slate-800 bg-[#0c1424] space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Utensils className="w-3.5 h-3.5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white">Meals & Refreshments</h4>
              <span className="text-[10px] font-mono text-slate-400">DGCA Para 3.8.1 (a)</span>
            </div>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {decision.meals ? (
              <span className="text-amber-300 font-medium">
                Mandatory free food and beverages in relation to waiting time.
              </span>
            ) : (
              'Not triggered for current waiting time threshold.'
            )}
          </p>
        </div>

        {/* Hotel Accommodation */}
        <div className="p-4 rounded-xl border border-slate-800 bg-[#0c1424] space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <Hotel className="w-3.5 h-3.5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white">Hotel Stay & Transfers</h4>
              <span className="text-[10px] font-mono text-slate-400">DGCA Para 3.4.3 / 3.8.1 (b)</span>
            </div>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {decision.hotel || stay?.owed_by_airline ? (
              <span className="text-purple-300 font-medium">
                Mandatory hotel room with airport cab transfers provided free of cost.
              </span>
            ) : (
              'Overnight hotel stay not mandatory for daytime delays under 24 hours.'
            )}
          </p>
        </div>

        {/* Rebooking Choice */}
        <div className="p-4 rounded-xl border border-slate-800 bg-[#0c1424] space-y-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-teal-500/10 text-teal-400 flex items-center justify-center">
              <RotateCcw className="w-3.5 h-3.5" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-white">Rebooking Option</h4>
              <span className="text-[10px] font-mono text-slate-400">DGCA Para 3.4.2 / 3.3.5</span>
            </div>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {decision.alt_or_refund || (isDelay && delayMinutes >= 360) ? (
              <span className="text-teal-300 font-medium">
                Full legal right to choose between immediate 100% refund or alternate rebooking.
              </span>
            ) : (
              'Current delay is under 6 hours; your ticket remains valid for the delayed flight.'
            )}
          </p>
        </div>
      </div>

      {/* Official Grievance Notice Preview */}
      <Card className="p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-white">
              Generated Statutory Grievance Notice
            </h3>
            <p className="text-xs text-slate-400">
              Customize with your details and copy to submit to the airline's appellate authority.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleCopyNotice}>
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Notice Text'}</span>
            </Button>
            <Button size="sm" onClick={handlePrint}>
              <Printer className="w-3.5 h-3.5" />
              <span>Print Document</span>
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 rounded-xl bg-slate-950 border border-slate-850 text-xs">
          <div>
            <label className="text-slate-400 block mb-1">Your Full Name:</label>
            <input
              type="text"
              value={passengerName}
              onChange={(e) => setPassengerName(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white"
            />
          </div>
          <div>
            <label className="text-slate-400 block mb-1">Booking PNR / Ticket Number:</label>
            <input
              type="text"
              value={pnr}
              onChange={(e) => setPnr(e.target.value.toUpperCase())}
              className="w-full bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-white uppercase font-mono"
            />
          </div>
        </div>

        <div className="bg-[#070b14] p-4 rounded-xl border border-slate-850 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto">
          {claimNoticeText}
        </div>
      </Card>

      {/* DGCA Clauses Cited */}
      {decision.clauses && decision.clauses.length > 0 && (
        <Card className="p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-200">
              Official DGCA Regulatory Paragraphs Cited
            </h4>
            <Link to="/evidence" className="text-xs text-teal-400 hover:underline flex items-center gap-1">
              <span>View Policy Evidence</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>

          <div className="flex flex-wrap gap-2">
            {decision.clauses.map((clauseId) => (
              <Link
                key={clauseId}
                to={`/evidence?q=${encodeURIComponent(clauseId)}`}
                className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 hover:border-teal-500 text-xs font-mono text-teal-300 transition-colors"
              >
                Para {clauseId}
              </Link>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

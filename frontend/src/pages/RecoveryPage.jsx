import React, { useState } from 'react';
import {
  Plane,
  Clock,
  ArrowRight,
  CheckCircle,
  Hotel,
  Search,
  ExternalLink,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { useSession } from '../context/SessionContext';
import { getFlightInfo, generateRecoveryPlan } from '../services/api';

export function RecoveryPage() {
  const { activePlan, setActivePlan, knownFacts, setKnownFacts } = useSession();

  const [searchFlight, setSearchFlight] = useState('6E204');
  const [flightStatusResult, setFlightStatusResult] = useState(null);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [simulating, setSimulating] = useState(false);

  const alternatives = activePlan?.alternatives || [];
  const stay = activePlan?.stay;

  const handleFlightLookup = async (e) => {
    e.preventDefault();
    if (!searchFlight.trim()) return;
    setLoadingSearch(true);
    setSearchError(null);
    try {
      const data = await getFlightInfo(searchFlight.trim());
      setFlightStatusResult(data);
    } catch (err) {
      setSearchError(err.message || 'Flight not found in current AirLabs schedule window.');
      setFlightStatusResult(null);
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleSelectAlternative = async (altFlight) => {
    setSimulating(true);
    try {
      const updatedScenario = {
        ...(knownFacts || {}),
        alternate_flight_offered: true,
        alternate_flight_accepted: true,
      };
      const plan = await generateRecoveryPlan(updatedScenario);
      setActivePlan(plan);
      setKnownFacts(updatedScenario);
    } catch (err) {
      console.error('Rebooking simulation error:', err);
    } finally {
      setSimulating(false);
    }
  };

  const formatTime = (isoString) => {
    try {
      return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-teal-400 font-mono text-xs">
          <Plane className="w-4 h-4" />
          <span>AirLabs Flight Data Engine Integration</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-extrabold text-white">
          Flight Recovery & Alternative Rebooking
        </h1>
        <p className="text-xs text-slate-400">
          Real-time alternative commercial departures and statutory duty-of-care arrangements (Para 3.4.2 / 3.3.5 / 3.8).
        </p>
      </div>

      {/* Flight Search Widget */}
      <Card className="p-5 space-y-4">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Search className="w-4 h-4 text-teal-400" />
          <span>Live AirLabs Flight Status Lookup</span>
        </h3>
        <form onSubmit={handleFlightLookup} className="flex gap-2">
          <Input
            type="text"
            value={searchFlight}
            onChange={(e) => setSearchFlight(e.target.value.toUpperCase())}
            placeholder="Enter flight number (e.g. 6E204, AI504)..."
            className="font-mono text-xs uppercase max-w-xs"
          />
          <Button type="submit" disabled={loadingSearch} size="default">
            {loadingSearch ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Query AirLabs'}
          </Button>
        </form>

        {searchError && (
          <div className="text-xs text-rose-400 font-mono bg-rose-500/10 p-2.5 rounded border border-rose-500/20">
            {searchError}
          </div>
        )}

        {flightStatusResult && (
          <div className="p-4 rounded-xl bg-[#080d1a] border border-slate-800 space-y-2 text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <span className="font-bold text-white font-mono text-sm">
                {flightStatusResult.flight_number} · {flightStatusResult.airline_name || flightStatusResult.airline}
              </span>
              <Badge variant="navy" className="capitalize">
                {flightStatusResult.status}
              </Badge>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px] text-slate-300">
              <div>
                <span className="text-slate-500 block">Sector</span>
                <span>{flightStatusResult.origin} → {flightStatusResult.destination}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Departure</span>
                <span>{formatTime(flightStatusResult.departure)}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Arrival</span>
                <span>{formatTime(flightStatusResult.arrival)}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Terminal / Gate</span>
                <span>T{flightStatusResult.departure_terminal || '1'} {flightStatusResult.departure_gate ? `· G${flightStatusResult.departure_gate}` : ''}</span>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Hotel & Care Obligations */}
      {stay && (
        <Card className="p-5 space-y-2 border-purple-500/30 bg-purple-950/10">
          <div className="flex items-center gap-2">
            <Hotel className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-bold text-white">
              Overnight Hotel Accommodation & Cab Transfers
            </h3>
            <Badge variant={stay.owed_by_airline ? 'success' : 'secondary'}>
              {stay.owed_by_airline ? 'Owed by Operating Carrier' : 'Not Mandatory'}
            </Badge>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            {stay.note || 'The airline is legally mandated to provide hotel accommodation and transfers where DGCA Para 3.4.3 / 3.8 applies.'}
          </p>
        </Card>
      )}

      {/* Alternative Flights Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-200">
            Available Commercial Rebooking Options
          </h2>
          <span className="text-xs font-mono text-slate-400">
            {alternatives.length} live schedules retrieved
          </span>
        </div>

        {alternatives.length === 0 ? (
          <Card className="p-8 text-center text-xs text-slate-500 space-y-2">
            <p>No live alternative flights were returned by AirLabs for this sector and time window.</p>
            <p className="text-[11px] text-slate-600">
              Tip: Run an assessment with major Indian city pairs like DEL → BOM or DEL → BLR to see live schedule streams.
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {alternatives.map((flight) => (
              <Card key={flight.flight_number + flight.departure} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-slate-700">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 font-mono font-bold text-xs flex items-center justify-center shrink-0">
                    {flight.airline_code || flight.airline || 'FL'}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white font-mono">
                        {flight.flight_number}
                      </span>
                      <span className="text-xs text-slate-400">
                        {flight.display_name || flight.airline_name}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                      {flight.origin} → {flight.destination} · {flight.duration_minutes} min
                      {flight.departure_terminal && ` · Terminal ${flight.departure_terminal}`}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6 text-xs">
                  <div>
                    <span className="text-[10px] text-slate-500 block">Departure</span>
                    <span className="font-mono font-bold text-white">
                      {formatTime(flight.departure)}
                    </span>
                  </div>
                  <div className="text-slate-600">→</div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Arrival</span>
                    <span className="font-mono font-bold text-white">
                      {formatTime(flight.arrival)}
                    </span>
                  </div>

                  <Button
                    size="sm"
                    variant="navy"
                    disabled={simulating}
                    onClick={() => handleSelectAlternative(flight)}
                    className="whitespace-nowrap"
                  >
                    <span>Simulate Rebooking</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-1" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

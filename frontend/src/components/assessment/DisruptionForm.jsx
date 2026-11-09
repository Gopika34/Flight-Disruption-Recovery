import React, { useState } from 'react';
import {
  Clock,
  Ban,
  UserX,
  ArrowDownCircle,
  Plane,
  ArrowRight,
  AlertCircle,
  DollarSign,
  Calendar,
  HelpCircle,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input, Select } from '../ui/input';
import { Badge } from '../ui/badge';

const AIRPORTS = [
  { code: 'DEL', city: 'Delhi', name: 'Indira Gandhi International', lat: 28.5562, lon: 77.1000 },
  { code: 'BOM', city: 'Mumbai', name: 'Chhatrapati Shivaji Maharaj', lat: 19.0896, lon: 72.8656 },
  { code: 'BLR', city: 'Bengaluru', name: 'Kempegowda International', lat: 13.1986, lon: 77.7066 },
  { code: 'HYD', city: 'Hyderabad', name: 'Rajiv Gandhi International', lat: 17.2403, lon: 78.4294 },
  { code: 'CCU', city: 'Kolkata', name: 'Netaji Subhash Chandra Bose', lat: 22.6547, lon: 88.4467 },
  { code: 'MAA', city: 'Chennai', name: 'Chennai International', lat: 12.9941, lon: 80.1709 },
  { code: 'GOI', city: 'Goa', name: 'Dabolim Airport', lat: 15.3808, lon: 73.8314 },
  { code: 'COK', city: 'Kochi', name: 'Cochin International', lat: 10.1518, lon: 76.3930 },
  { code: 'AMD', city: 'Ahmedabad', name: 'Sardar Vallabhbhai Patel', lat: 23.0772, lon: 72.6347 },
  { code: 'PNQ', city: 'Pune', name: 'Pune Airport', lat: 18.5822, lon: 73.9197 },
  { code: 'DXB', city: 'Dubai', name: 'Dubai International', lat: 25.2532, lon: 55.3657 },
  { code: 'SIN', city: 'Singapore', name: 'Singapore Changi', lat: 1.3644, lon: 103.9915 },
  { code: 'LHR', city: 'London', name: 'London Heathrow', lat: 51.4700, lon: -0.4543 },
];

export function DisruptionForm({ formData, setFormData, onSubmit, loading, missingFacts = [] }) {
  const isMissing = (fact) => missingFacts.includes(fact);

  const handleTypeChange = (type) => {
    setFormData((prev) => {
      const next = {
        ...prev,
        type,
      };
      if (type === 'delay') {
        next.delay_minutes = next.delay_minutes ?? 240;
        next.total_delay_from_published_minutes = next.delay_minutes ?? 240;
        next.checked_in_on_time = true;
        next.domestic = true;
        next.reason = next.reason || 'operational';
      } else if (type === 'cancellation') {
        next.notice_hours = next.notice_hours ?? 12;
        next.has_contact_info = true;
        next.alternate_flight_offered = false;
        next.basic_fare = next.basic_fare ?? 4500;
        next.fuel_charge = next.fuel_charge ?? 1200;
        next.reason = next.reason || 'operational';
      } else if (type === 'denied_boarding') {
        next.confirmed_booking = true;
        next.checked_in_on_time = true;
        next.voluntary_surrender = false;
        next.overbooking = true;
        next.alternate_flight_offered = false;
        next.connecting_same_ticket = false;
        next.basic_fare = next.basic_fare ?? 3500;
        next.fuel_charge = next.fuel_charge ?? 1200;
      } else if (type === 'downgrading') {
        next.sector = 'domestic';
        next.ticket_amount_including_taxes = next.ticket_amount_including_taxes ?? 12000;
        next.involuntary = true;
      }
      return next;
    });
  };

  return (
    <form onSubmit={onSubmit} className="p-6 rounded-2xl border border-slate-800 bg-[#0c1424] space-y-6">
      {/* Disruption Type Switcher */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-300 block">
          Select Disruption Category
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <button
            type="button"
            onClick={() => handleTypeChange('delay')}
            className={`flex items-center justify-center gap-2 p-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
              formData.type === 'delay'
                ? 'bg-amber-500/10 border-amber-500/50 text-amber-300 shadow-sm'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>Flight Delay</span>
          </button>

          <button
            type="button"
            onClick={() => handleTypeChange('cancellation')}
            className={`flex items-center justify-center gap-2 p-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
              formData.type === 'cancellation'
                ? 'bg-rose-500/10 border-rose-500/50 text-rose-300 shadow-sm'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Ban className="w-3.5 h-3.5" />
            <span>Cancellation</span>
          </button>

          <button
            type="button"
            onClick={() => handleTypeChange('denied_boarding')}
            className={`flex items-center justify-center gap-2 p-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
              formData.type === 'denied_boarding'
                ? 'bg-teal-500/10 border-teal-500/50 text-teal-300 shadow-sm'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <UserX className="w-3.5 h-3.5" />
            <span>Denied Boarding</span>
          </button>

          <button
            type="button"
            onClick={() => handleTypeChange('downgrading')}
            className={`flex items-center justify-center gap-2 p-2.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
              formData.type === 'downgrading'
                ? 'bg-sky-500/10 border-sky-500/50 text-sky-300 shadow-sm'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <ArrowDownCircle className="w-3.5 h-3.5" />
            <span>Downgrade</span>
          </button>
        </div>
      </div>

      {/* Flight & Route Section */}
      <div className="space-y-4 pt-2 border-t border-slate-800">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
            <Plane className="w-4 h-4 text-teal-400" />
            <span>Flight & Route Information</span>
          </span>
          <span className="text-[11px] font-mono text-slate-500">
            Validated against AirLabs IATA database
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-slate-400 block mb-1">Flight Number</label>
            <Input
              type="text"
              placeholder="e.g. 6E204, AI504"
              value={formData.flight_number || ''}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, flight_number: e.target.value.toUpperCase() }))
              }
              className="font-mono uppercase"
            />
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Origin Airport</label>
            <Select
              value={formData.origin || 'DEL'}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, origin: e.target.value.toUpperCase() }))
              }
              className="font-mono"
            >
              {AIRPORTS.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.code} - {a.city} ({a.name})
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className="text-xs text-slate-400 block mb-1">Destination Airport</label>
            <Select
              value={formData.destination || 'BOM'}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, destination: e.target.value.toUpperCase() }))
              }
              className="font-mono"
            >
              {AIRPORTS.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.code} - {a.city} ({a.name})
                </option>
              ))}
            </Select>
          </div>

          <div>
            <label className={`text-xs block mb-1 ${isMissing('scheduled_departure') ? 'text-amber-400 font-bold' : 'text-slate-400'}`}>
              Scheduled Departure (24h)
            </label>
            <Input
              type="text"
              placeholder="HH:MM (e.g. 21:00)"
              value={formData.scheduled_departure || ''}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, scheduled_departure: e.target.value }))
              }
              className={`font-mono ${isMissing('scheduled_departure') ? 'border-amber-500' : ''}`}
            />
          </div>
        </div>
      </div>

      {/* Disruption Specific Fields */}
      <div className="space-y-4 pt-4 border-t border-slate-800">
        {/* DELAY FIELDS */}
        {formData.type === 'delay' && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className={`text-xs block mb-1 ${isMissing('delay_minutes') ? 'text-amber-400 font-bold' : 'text-slate-400'}`}>
                Delay Minutes
              </label>
              <Input
                type="number"
                min="0"
                step="10"
                value={formData.delay_minutes ?? 240}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    delay_minutes: Number(e.target.value),
                    total_delay_from_published_minutes: Number(e.target.value),
                  }))
                }
                className="font-mono"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                {Math.floor((formData.delay_minutes || 0) / 60)}h {(formData.delay_minutes || 0) % 60}m delay
              </span>
            </div>

            <div>
              <label className={`text-xs block mb-1 ${isMissing('reason') ? 'text-amber-400 font-bold' : 'text-slate-400'}`}>
                Airline-Stated Reason
              </label>
              <Select
                value={formData.reason || 'operational'}
                onChange={(e) => setFormData((prev) => ({ ...prev, reason: e.target.value }))}
              >
                <option value="operational">Operational Reasons (Airline control)</option>
                <option value="technical">Technical / Maintenance Snag</option>
                <option value="crew_shortage">Crew Shortage / Rostering</option>
                <option value="weather">Adverse Weather (Burden of proof required)</option>
                <option value="atc">Air Traffic Control (ATC flow restriction)</option>
              </Select>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">
                Scheduled Flight Duration (min)
              </label>
              <Input
                type="number"
                min="20"
                value={formData.block_time_minutes ?? 130}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, block_time_minutes: Number(e.target.value) }))
                }
                className="font-mono"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">
                Block time determines meal tier (Para 3.4.1)
              </span>
            </div>

            <div className="sm:col-span-3 flex flex-wrap items-center gap-6 pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.checked_in_on_time ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, checked_in_on_time: e.target.checked }))
                  }
                  className="rounded text-teal-500 bg-slate-900 border-slate-700"
                />
                <span>Passenger checked in on time</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.domestic ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, domestic: e.target.checked }))
                  }
                  className="rounded text-teal-500 bg-slate-900 border-slate-700"
                />
                <span>Domestic Indian sector (Para 3.4.2 6h refund mandate)</span>
              </label>
            </div>
          </div>
        )}

        {/* CANCELLATION FIELDS */}
        {formData.type === 'cancellation' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className={`text-xs block mb-1 ${isMissing('notice_hours') ? 'text-amber-400 font-bold' : 'text-slate-400'}`}>
                  Notice Given (Hours Before Departure)
                </label>
                <Input
                  type="number"
                  min="0"
                  value={formData.notice_hours ?? 12}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, notice_hours: Number(e.target.value) }))
                  }
                  className="font-mono"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  &lt;24h notice triggers Para 3.3.2 compensation
                </span>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Basic Fare (₹ INR, no tax)</label>
                <Input
                  type="number"
                  min="0"
                  value={formData.basic_fare ?? 4500}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, basic_fare: Number(e.target.value) }))
                  }
                  className="font-mono"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">Fuel Charge (₹ INR, no tax)</label>
                <Input
                  type="number"
                  min="0"
                  value={formData.fuel_charge ?? 1200}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, fuel_charge: Number(e.target.value) }))
                  }
                  className="font-mono"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6 pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.has_contact_info ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, has_contact_info: e.target.checked }))
                  }
                  className="rounded text-teal-500 bg-slate-900 border-slate-700"
                />
                <span>Contact details (phone/email) provided during booking</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.alternate_flight_offered ?? false}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, alternate_flight_offered: e.target.checked }))
                  }
                  className="rounded text-teal-500 bg-slate-900 border-slate-700"
                />
                <span>Alternate flight offered by carrier</span>
              </label>
            </div>
          </div>
        )}

        {/* DENIED BOARDING FIELDS */}
        {formData.type === 'denied_boarding' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Basic Fare (₹ INR)</label>
                <Input
                  type="number"
                  min="0"
                  value={formData.basic_fare ?? 3500}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, basic_fare: Number(e.target.value) }))
                  }
                  className="font-mono"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Fuel Charge (₹ INR)</label>
                <Input
                  type="number"
                  min="0"
                  value={formData.fuel_charge ?? 1200}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, fuel_charge: Number(e.target.value) }))
                  }
                  className="font-mono"
                />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-6 pt-2">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.confirmed_booking ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, confirmed_booking: e.target.checked }))
                  }
                  className="rounded text-teal-500"
                />
                <span>Confirmed Reservation</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.checked_in_on_time ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, checked_in_on_time: e.target.checked }))
                  }
                  className="rounded text-teal-500"
                />
                <span>Checked in on time</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={formData.overbooking ?? true}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, overbooking: e.target.checked }))
                  }
                  className="rounded text-teal-500"
                />
                <span>Denied due to overbooking</span>
              </label>
            </div>
          </div>
        )}

        {/* DOWNGRADING FIELDS */}
        {formData.type === 'downgrading' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Sector Type</label>
              <Select
                value={formData.sector || 'domestic'}
                onChange={(e) => setFormData((prev) => ({ ...prev, sector: e.target.value }))}
              >
                <option value="domestic">Domestic India (Mandatory 75% refund)</option>
                <option value="international">International Flight (30% - 75%)</option>
              </Select>
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1">
                Ticket Amount Including Taxes (₹ INR)
              </label>
              <Input
                type="number"
                min="0"
                value={formData.ticket_amount_including_taxes ?? 12000}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    ticket_amount_including_taxes: Number(e.target.value),
                  }))
                }
                className="font-mono"
              />
              <span className="text-[11px] text-teal-400 mt-1 block font-mono">
                Statutory 75% Refund = ₹{((formData.ticket_amount_including_taxes || 12000) * 0.75).toLocaleString('en-IN')}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        <span className="text-xs text-slate-500">
          Evaluated via verified Python DGCA engine on Render.
        </span>

        <Button type="submit" disabled={loading} size="lg" className="w-full sm:w-auto font-bold">
          {loading ? (
            <span>Computing Statutory Entitlements...</span>
          ) : (
            <>
              <span>Evaluate Disruption Rights</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </>
          )}
        </Button>
      </div>
    </form>
  );
}

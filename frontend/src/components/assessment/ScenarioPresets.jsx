import React from 'react';
import { Sparkles, Clock, Ban, UserX, ArrowDownCircle } from 'lucide-react';
import { Badge } from '../ui/badge';

export const PRESET_SCENARIOS = [
  {
    id: 'delay_night_del_bom',
    title: 'Severe Evening Delay (IndiGo DEL → BOM)',
    category: 'delay',
    description: '4-hour evening delay on Delhi to Mumbai departing at 21:00. Triggers Para 3.4.1 meals & Para 3.4.3 hotel stay requirement.',
    payload: {
      type: 'delay',
      reason: 'operational',
      flight_number: '6E204',
      origin: 'DEL',
      destination: 'BOM',
      scheduled_departure: '21:00',
      delay_minutes: 240,
      total_delay_from_published_minutes: 240,
      block_time_minutes: 130,
      checked_in_on_time: true,
      domestic: true,
    },
  },
  {
    id: 'cancellation_short_notice',
    title: 'Short-Notice Flight Cancellation (Air India DEL → BLR)',
    category: 'cancellation',
    description: '12h advance notice given with no alternate flight accepted. Triggers statutory compensation (₹5,700) + 100% full ticket refund.',
    payload: {
      type: 'cancellation',
      reason: 'operational',
      flight_number: 'AI504',
      origin: 'DEL',
      destination: 'BLR',
      scheduled_departure: '10:00',
      notice_hours: 12,
      has_contact_info: true,
      alternate_flight_offered: false,
      block_time_minutes: 175,
      basic_fare: 4500,
      fuel_charge: 1200,
    },
  },
  {
    id: 'denied_boarding_overbooked',
    title: 'Involuntary Denied Boarding (SpiceJet BOM → DEL)',
    category: 'denied_boarding',
    description: 'Confirmed passenger checked in on time but bumped due to overbooking with no alternate. 400% compensation up to ₹20,000 + full refund.',
    payload: {
      type: 'denied_boarding',
      flight_number: 'SG8152',
      origin: 'BOM',
      destination: 'DEL',
      scheduled_departure: '08:30',
      confirmed_booking: true,
      checked_in_on_time: true,
      voluntary_surrender: false,
      overbooking: true,
      alternate_flight_offered: false,
      connecting_same_ticket: false,
      basic_fare: 3500,
      fuel_charge: 1200,
    },
  },
  {
    id: 'downgrade_domestic_ticket',
    title: 'Cabin Downgrade (Vistara Business → Economy)',
    category: 'downgrading',
    description: 'Involuntary downgrade on DEL → CCU with ticket price of ₹12,000. Statutory 75% refund of ticket amount including taxes (₹9,000).',
    payload: {
      type: 'downgrading',
      sector: 'domestic',
      flight_number: 'UK778',
      origin: 'DEL',
      destination: 'CCU',
      scheduled_departure: '14:15',
      ticket_amount_including_taxes: 12000,
      involuntary: true,
    },
  },
];

export function ScenarioPresets({ onSelectPreset }) {
  return (
    <div className="p-4 rounded-xl border border-slate-800 bg-[#0c1424] space-y-3">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
        <Sparkles className="w-4 h-4 text-teal-400" />
        <span>1-Click Test Scenarios (Grounded in DGCA Cases)</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {PRESET_SCENARIOS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            onClick={() => onSelectPreset(preset.payload)}
            className="text-left p-3 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800/80 hover:border-slate-700 transition-all group cursor-pointer"
          >
            <div className="flex items-center justify-between gap-1 mb-1">
              <span className="text-xs font-semibold text-slate-200 group-hover:text-teal-400 transition-colors truncate">
                {preset.title}
              </span>
              <Badge variant="secondary" className="text-[9px] uppercase px-1 py-0">
                {preset.category}
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
              {preset.description}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

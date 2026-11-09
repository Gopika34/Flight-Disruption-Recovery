import React from 'react';
import { Link } from 'react-router-dom';
import { Plane, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';

export function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4 space-y-4">
      <div className="w-12 h-12 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center">
        <Plane className="w-6 h-6 rotate-90" />
      </div>
      <h1 className="text-xl font-bold text-white">404 — Flight Route Not Found</h1>
      <p className="text-xs text-slate-400 max-w-sm">
        The requested screen does not exist. Return to FlightGuard overview or start a disruption claim.
      </p>
      <Link to="/">
        <Button size="sm">
          <ArrowLeft className="w-4 h-4 mr-1.5" />
          <span>Return Home</span>
        </Button>
      </Link>
    </div>
  );
}

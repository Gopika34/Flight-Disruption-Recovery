import React from 'react';
import { GitHubConnector } from '../components/connectors/GitHubConnector';

export function IntegrationsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-400">Workspace settings</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-white">Integrations</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">Connect external services that FlightGuard's AI agent can access through permission-checked tools.</p>
      </div>
      <GitHubConnector />
    </div>
  );
}

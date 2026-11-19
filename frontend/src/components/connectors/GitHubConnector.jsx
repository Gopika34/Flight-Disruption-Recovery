import React,{ useEffect, useState} from 'react';
import { Github, Link2, Unlink, LoaderCircle, ShieldCheck } from 'lucide-react';
import { apiClient } from '../../services/api';

export function GitHubConnector() {
  const [status, setStatus] = useState({ loading: true, connected: false, account: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function refresh() {
    setStatus((old) => ({ ...old, loading: true }));
    try {
      const { data } = await apiClient.get('/connectors/github/status');
      setStatus({ loading: false, connected: Boolean(data.connected), account: data.account || null });
    } catch (err) {
      setStatus({ loading: false, connected: false, account: null });
      setError(err.message || 'Could not load GitHub connection status.');
    }
  }

  useEffect(() => { refresh(); }, []);

  async function connect() {
    setBusy(true); setError('');
    try {
      const { data } = await apiClient.post('/connectors/github/oauth/start');
      if (!data.authorization_url) throw new Error('The server did not return a GitHub authorization URL.');
      window.location.assign(data.authorization_url);
    } catch (err) {
      setError(err.message || 'Could not start GitHub authorization.');
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true); setError('');
    try {
      await apiClient.delete('/connectors/github');
      await refresh();
    } catch (err) {
      setError(err.message || 'Could not disconnect GitHub.');
    } finally { setBusy(false); }
  }

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 sm:p-6">
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-slate-700 bg-slate-950 text-white">
          <Github className="h-6 w-6" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-white">GitHub</h2>
            <span className={`rounded-full px-2.5 py-1 text-xs ${status.connected ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-800 text-slate-400'}`}>
              {status.loading ? 'Checking…' : status.connected ? 'Connected' : 'Not connected'}
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">Allow FlightGuard AI agent to search code, list repositories, read files and inspect issues through read-only MCP tools.</p>
          {status.account?.login && <p className="mt-3 text-sm text-slate-300">Connected as <strong>@{status.account.login}</strong> <span className="text-slate-500">({status.account.auth_type || 'OAuth'})</span></p>}
          <div className="mt-4 flex flex-wrap gap-2">
            {status.connected ? (
              <button disabled={busy} onClick={disconnect} className="inline-flex items-center gap-2 rounded-lg border border-rose-500/30 px-3 py-2 text-sm font-medium text-rose-300 hover:bg-rose-500/10 disabled:opacity-50">
                {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Unlink className="h-4 w-4" />} Disconnect
              </button>
            ) : (
              <button disabled={busy || status.loading} onClick={connect} className="inline-flex items-center gap-2 rounded-lg bg-teal-400 px-3 py-2 text-sm font-semibold text-slate-950 hover:bg-teal-300 disabled:opacity-50">
                {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />} Connect GitHub
              </button>
            )}
            <button onClick={refresh} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-800">Refresh</button>
          </div>
          <div className="mt-4 flex items-start gap-2 text-xs leading-5 text-slate-500">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-teal-400" />
            OAuth credentials are encrypted at rest. FlightGuard exposes only allow-listed read operations. The GitHub App must be configured with read-only Contents, Issues and Metadata permissions; repository access is limited by both the app and the user.
          </div>
          {error && <p role="alert" className="mt-3 text-sm text-rose-300">{error}</p>}
        </div>
      </div>
    </section>
  );
}

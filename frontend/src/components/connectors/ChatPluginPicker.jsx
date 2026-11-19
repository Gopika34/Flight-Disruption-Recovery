
import React, { useEffect, useState } from 'react';
import {
  Github, Plug, CheckCircle2, LoaderCircle, X,
  ArrowLeft, Clock3
} from 'lucide-react';
import { apiClient } from '../../services/api';

const COMING_SOON = [
  { id: 'google_drive', name: 'Google Drive', detail: 'Search your files and documents' },
  { id: 'gmail', name: 'Gmail', detail: 'Find and summarize email threads' },
  { id: 'notion', name: 'Notion', detail: 'Search workspace pages and notes' },
  { id: 'slack', name: 'Slack', detail: 'Search messages and channels' },
  { id: 'linear', name: 'Linear', detail: 'Look up issues and projects' },
];

export function ChatPluginPicker({ onClose }) {
  const [selected, setSelected] = useState(null);
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState(null);
  const [pat, setPat] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function refresh() {
    try {
      const { data } = await apiClient.get('/connectors/github/status');
      setConnected(Boolean(data.connected));
      setAccount(data.account || null);
      setError('');
    } catch (err) {
      setError(err.message || 'Could not check GitHub connection.');
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function connectGitHub(event) {
    event.preventDefault();

    if (!pat.trim()) return;

    setBusy(true);
    setError('');
    setNotice('');

    try {
      const { data } = await apiClient.post('/connectors/github/connect', {
        personal_access_token: pat.trim(),
      });

      setConnected(Boolean(data.connected));
      setAccount(data.account || null);
      setPat('');
      setNotice(
        `Connected to GitHub${data.account?.login ? ` as @${data.account.login}` : ''}.`
      );
    } catch (err) {
      setError(err.message || 'GitHub connection failed.');
    } finally {
      setBusy(false);
    }
  }

  async function disconnectGitHub() {
    setBusy(true);
    setError('');
    setNotice('');

    try {
      await apiClient.delete('/connectors/github');
      setConnected(false);
      setAccount(null);
      setNotice('GitHub disconnected.');
    } catch (err) {
      setError(err.message || 'Could not disconnect GitHub.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-label="Connect plugins"
      className="
        absolute bottom-full left-0 z-50 mb-3
        w-[min(22rem,calc(100vw-2rem))]
        max-h-[min(70vh,34rem)] overflow-y-auto
        rounded-2xl border border-slate-700
        bg-[#0b1423] p-4
        shadow-2xl shadow-black/40
      "
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          {selected && (
            <button
              type="button"
              onClick={() => {
                setSelected(null);
                setError('');
                setNotice('');
              }}
              aria-label="Back to plugins"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
          )}

          <div>
            <p className="text-sm font-semibold text-white">
              {selected ? 'Connect GitHub' : 'Connect a plugin'}
            </p>
            <p className="mt-0.5 text-[11px] text-slate-400">
              {selected
                ? 'Connect your GitHub account securely.'
                : 'Give your assistant access to external tools.'}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close plugins"
          className="shrink-0 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {!selected ? (
        <div className="space-y-2">
          <button
            type="button"
            onClick={() => {
              setSelected('github');
              setError('');
              setNotice('');
            }}
            className="
              flex w-full items-center gap-3 rounded-xl
              border border-teal-500/30 bg-teal-500/5 p-3
              text-left transition hover:border-teal-400
              hover:bg-teal-500/10
            "
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-900 text-white">
              <Github className="h-5 w-5" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-white">GitHub</span>
                <span className="rounded-full bg-teal-400/10 px-2 py-0.5 text-[10px] text-teal-300">
                  Available
                </span>
              </div>
              <p className="mt-1 text-[11px] text-slate-400">
                Repositories, files, code and issues through MCP.
              </p>
            </div>

            {connected && <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />}
          </button>

          <div className="my-3 border-t border-slate-800" />

          {COMING_SOON.map((plugin) => (
            <div
              key={plugin.id}
              className="flex items-center gap-3 rounded-xl border border-slate-800/80 p-3 opacity-65"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-slate-400">
                <Plug className="h-4 w-4" />
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-slate-200">{plugin.name}</p>
                <p className="mt-1 text-[10px] text-slate-500">{plugin.detail}</p>
              </div>

              <span className="flex shrink-0 items-center gap-1 rounded-full bg-slate-800 px-2 py-1 text-[9px] text-slate-400">
                <Clock3 className="h-3 w-3" />
                Coming soon
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-xl border border-teal-500/20 bg-teal-500/5 p-3">
            <div className="flex items-center gap-2">
              <Github className="h-5 w-5 text-white" />
              <span className="text-sm font-semibold text-white">GitHub</span>
              {connected && (
                <span className="ml-auto text-[10px] text-emerald-300">Connected</span>
              )}
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-400">
              Connect your GitHub account to let FlightGuard search repositories,
              inspect files, search code and read issues.
            </p>
          </div>

          {connected ? (
            <div className="space-y-3">
              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <p className="text-xs text-emerald-300">
                  Connected{account?.login ? ` as @${account.login}` : ''}.
                </p>
              </div>

              <button
                type="button"
                disabled={busy}
                onClick={disconnectGitHub}
                className="w-full rounded-xl border border-rose-500/30 px-4 py-2.5 text-xs font-medium text-rose-300 hover:bg-rose-500/10 disabled:opacity-50"
              >
                {busy ? 'Disconnecting...' : 'Disconnect GitHub'}
              </button>
            </div>
          ) : (
            <form onSubmit={connectGitHub} className="space-y-3">
              <div>
                <label
                  htmlFor="github-pat"
                  className="mb-2 block text-xs font-medium text-slate-300"
                >
                  Personal Access Token
                </label>

                <input
                  id="github-pat"
                  type="password"
                  autoComplete="off"
                  value={pat}
                  onChange={(e) => setPat(e.target.value)}
                  placeholder="github_pat_..."
                  className="
                    w-full rounded-xl border border-slate-700
                    bg-slate-950 px-3 py-3 text-xs text-white
                    outline-none placeholder:text-slate-600
                    focus:border-teal-400
                  "
                />

                <p className="mt-2 text-[10px] leading-4 text-slate-500">
                  Use a fine-grained token with read-only Metadata,
                  Contents and Issues access for your selected repositories.
                </p>
              </div>

              <button
                type="submit"
                disabled={busy || !pat.trim()}
                className="
                  flex w-full items-center justify-center gap-2
                  rounded-xl bg-teal-500 px-4 py-3
                  text-xs font-semibold text-slate-950
                  transition hover:bg-teal-400
                  disabled:cursor-not-allowed disabled:opacity-50
                "
              >
                {busy ? (
                  <>
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                    Connecting...
                  </>
                ) : (
                  'Connect GitHub'
                )}
              </button>
            </form>
          )}

          <p className="text-[10px] leading-4 text-slate-500">
            Your PAT is sent to the backend over your authenticated session
            and encrypted before storage. Never paste it into the chat.
          </p>
        </div>
      )}

      {notice && (
        <p role="status" className="mt-3 text-xs text-emerald-300">
          {notice}
        </p>
      )}

      {error && (
        <p role="alert" className="mt-3 break-words text-xs text-rose-300">
          {error}
        </p>
      )}
    </div>
  );
}

import React from 'react';
import { SignInButton, SignUpButton, UserButton, useAuth } from '@clerk/react';

function ClerkControls() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return null;
  if (isSignedIn) return <div className="flex items-center gap-2"><span className="hidden sm:inline text-xs text-slate-400">Signed in</span><UserButton /></div>;
  return (
    <div className="flex items-center gap-2">
      <SignInButton mode="modal">
        <button className="rounded-lg border border-teal-500/40 px-3 py-2 text-xs font-semibold text-teal-300 hover:bg-teal-500/10">Sign in</button>
      </SignInButton>
      <SignUpButton mode="modal">
        <button className="hidden sm:inline-flex rounded-lg bg-teal-400 px-3 py-2 text-xs font-bold text-slate-950 hover:bg-teal-300">Create account</button>
      </SignUpButton>
    </div>
  );
}

export function AuthControls() {
  if (!import.meta.env.VITE_CLERK_PUBLISHABLE_KEY) {
    return <span className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-400">Guest mode</span>;
  }
  return <ClerkControls />;
}

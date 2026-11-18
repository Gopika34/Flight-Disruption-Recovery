import React, { useEffect, useState } from 'react';
import { useAuth } from '@clerk/react';
import { createOrReuseGuestSession, setAuthTokenGetter, clearGuestSession } from '../../services/authToken';

const OWNER_KEY = 'flightguard_local_owner';
const USER_DATA_KEYS = ['flightguard_session_id','flightguard_sessions_history','flightguard_known_facts','flightguard_active_plan','flightguard_sessions_messages'];

function switchLocalOwner(nextOwner) {
  const previous = localStorage.getItem(OWNER_KEY);
  if (previous && previous !== nextOwner) USER_DATA_KEYS.forEach((key) => localStorage.removeItem(key));
  localStorage.setItem(OWNER_KEY, nextOwner);
}

function BootstrapFrame({ children, hasClerk = false, isLoaded = true, isSignedIn = false, userId = null, getToken = null }) {
  const [ready, setReady] = useState(false);
  const [ownerId, setOwnerId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      try {
        if (hasClerk && !isLoaded) return;
        if (hasClerk && isSignedIn && userId) {
          clearGuestSession();
          const token = await getToken();
          if (!token) throw new Error('Clerk session token unavailable');
          setAuthTokenGetter(() => getToken());
          switchLocalOwner(userId);
          setOwnerId(userId);
        } else {
          const guest = await createOrReuseGuestSession();
          setAuthTokenGetter(async () => {
            if (hasClerk && isLoaded && isSignedIn) return getToken();
            const currentGuest = await createOrReuseGuestSession();
            return currentGuest.token;
          });
          switchLocalOwner(guest.userId);
          setOwnerId(guest.userId);
        }
        if (!cancelled) setReady(true);
      } catch (error) {
        console.error('Authentication bootstrap failed:', error);
        if (!cancelled) setReady(false);
      }
    }
    initialize();
    return () => { cancelled = true; };
  }, [hasClerk, isLoaded, isSignedIn, userId, getToken]);

  if (!ready) return <div className="min-h-screen bg-[#080d1a] text-slate-300 flex items-center justify-center">Preparing secure session…</div>;
  return <React.Fragment key={ownerId || 'guest'}>{children}</React.Fragment>;
}

export function ClerkAuthBootstrap({ children }) {
  const { isLoaded, isSignedIn, userId, getToken } = useAuth();
  return <BootstrapFrame hasClerk isLoaded={isLoaded} isSignedIn={isSignedIn} userId={userId} getToken={getToken}>{children}</BootstrapFrame>;
}

export function GuestAuthBootstrap({ children }) {
  return <BootstrapFrame>{children}</BootstrapFrame>;
}

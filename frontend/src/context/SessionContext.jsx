import React, { createContext, useContext, useState, useEffect } from 'react';

const SessionContext = createContext(null);

const STORAGE_KEY_CURRENT = 'flightguard_session_id';
const STORAGE_KEY_LIST = 'flightguard_sessions_history';
const STORAGE_KEY_FACTS = 'flightguard_known_facts';
const STORAGE_KEY_PLAN = 'flightguard_active_plan';
const STORAGE_KEY_MESSAGES = 'flightguard_sessions_messages';

export function SessionProvider({ children }) {
  const [sessionId, setSessionId] = useState(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_CURRENT);
      if (raw && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(raw)) {
        return raw;
      }
      localStorage.removeItem(STORAGE_KEY_CURRENT);
      return null;
    } catch {
      return null;
    }
  });

  const [sessionList, setSessionList] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_LIST);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [sessionMessages, setSessionMessages] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_MESSAGES);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const [knownFacts, setKnownFacts] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_FACTS);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const [activePlan, setActivePlan] = useState(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_PLAN);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  // Sync to localStorage
  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEY_CURRENT, sessionId);
    } else {
      localStorage.removeItem(STORAGE_KEY_CURRENT);
    }
  }, [sessionId]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_LIST, JSON.stringify(sessionList));
  }, [sessionList]);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(sessionMessages));
    } catch (e) {
      console.warn('Failed to save session messages to localStorage', e);
    }
  }, [sessionMessages]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY_FACTS, JSON.stringify(knownFacts));
  }, [knownFacts]);

  useEffect(() => {
    if (activePlan) {
      localStorage.setItem(STORAGE_KEY_PLAN, JSON.stringify(activePlan));
    } else {
      localStorage.removeItem(STORAGE_KEY_PLAN);
    }
  }, [activePlan]);

  const saveSessionMessages = (id, msgs) => {
    if (!id || !Array.isArray(msgs)) return;
    setSessionMessages((prev) => ({
      ...prev,
      [id]: msgs,
    }));
  };

  const getSessionMessages = (id) => {
    if (!id) return null;
    return sessionMessages[id] || null;
  };

  const recordSession = (id, metadata = {}) => {
    setSessionId(id);
    setSessionList((prev) => {
      const existingIdx = prev.findIndex((s) => s.id === id);
      const updatedItem = {
        id,
        title: metadata.title || metadata.flight_number || 'Flight Assessment',
        type: metadata.type || 'disruption',
        flightNumber: metadata.flight_number || null,
        status: metadata.status || 'in_progress',
        lastUpdated: Date.now(),
        summary: metadata.summary || null,
      };

      if (existingIdx >= 0) {
        const nextList = [...prev];
        nextList[existingIdx] = { ...nextList[existingIdx], ...updatedItem };
        return nextList;
      }
      return [updatedItem, ...prev].slice(0, 20); // Keep last 20
    });
  };

  const startNewSession = () => {
    setSessionId(null);
    setKnownFacts({});
    setActivePlan(null);
    localStorage.removeItem(STORAGE_KEY_CURRENT);
    localStorage.removeItem(STORAGE_KEY_FACTS);
    localStorage.removeItem(STORAGE_KEY_PLAN);
  };

  const deleteSession = (id) => {
    setSessionList((prev) => prev.filter((s) => s.id !== id));
    setSessionMessages((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });
    if (sessionId === id) {
      startNewSession();
    }
  };

  return (
    <SessionContext.Provider
      value={{
        sessionId,
        setSessionId,
        sessionList,
        recordSession,
        startNewSession,
        deleteSession,
        knownFacts,
        setKnownFacts,
        activePlan,
        setActivePlan,
        sessionMessages,
        saveSessionMessages,
        getSessionMessages,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}

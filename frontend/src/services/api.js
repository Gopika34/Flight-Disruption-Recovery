import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 35000,
});

export function formatApiError(data, fallback = 'An unexpected error occurred.') {
  if (!data) return fallback;
  if (typeof data === 'string') return data;
  if (data instanceof Error) {
    return data.message || fallback;
  }
  if (Array.isArray(data)) {
    return data
      .map((item) => {
        if (!item) return '';
        if (typeof item === 'string') return item;
        const loc = item.loc ? item.loc.slice(1).join('.') : '';
        const msg = item.msg || item.message || '';
        return loc && msg ? `${loc}: ${msg}` : (msg || JSON.stringify(item));
      })
      .filter(Boolean)
      .join('; ') || fallback;
  }
  if (data.detail) {
    return formatApiError(data.detail, fallback);
  }
  if (data.message) {
    return typeof data.message === 'string' ? data.message : formatApiError(data.message, fallback);
  }
  if (data.error) {
    const errText = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
    return data.message ? `${errText}: ${formatApiError(data.message, '')}` : errText;
  }
  try {
    const str = JSON.stringify(data);
    return str === '{}' ? fallback : str;
  } catch {
    return fallback;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'An unexpected network error occurred.';
    if (error.response?.data) {
      message = formatApiError(error.response.data);
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

export function isValidUUID(id) {
  return typeof id === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}

// 1. Health & Status
export async function getLiveHealth() {
  const { data } = await apiClient.get('/health/live');
  return data;
}

export async function getReadyHealth() {
  const { data } = await apiClient.get('/health/ready');
  return data;
}

export async function getLlmStatus() {
  const { data } = await apiClient.get('/llm/status');
  return data;
}

// 2. Policy Vector RAG Search
export async function searchPolicies(query, k = 4) {
  const { data } = await apiClient.get('/search', {
    params: { q: query, k },
  });
  return data;
}

// 3. Live Flight Feeds (AirLabs)
export async function getFlightInfo(flightNumber) {
  const { data } = await apiClient.get(`/flights/${flightNumber.trim().toUpperCase()}`);
  return data;
}

// 4. Deterministic Evaluation
export async function evaluateDisruption(scenario) {
  const { data } = await apiClient.post('/evaluate', cleanScenarioPayload(scenario));
  return data;
}

// 5. Complete Recovery Plan
export async function generateRecoveryPlan(scenario) {
  const { data } = await apiClient.post('/recover', cleanScenarioPayload(scenario));
  return data;
}

// 6. Conversational Interface (REST)
export async function askAssistant(message, sessionId = null, knownFacts = {}) {
  const payload = {
    message,
    known_facts: cleanScenarioPayload(knownFacts),
  };
  if (isValidUUID(sessionId)) {
    payload.session_id = sessionId;
  }
  const { data } = await apiClient.post('/ask', payload);
  return data;
}

// 7. Native SSE Streaming (/ask/stream)
export async function streamAskAssistant({
  message,
  sessionId = null,
  knownFacts = {},
  onEvent,
  onError,
  onComplete,
}) {
  const payload = {
    message,
    known_facts: cleanScenarioPayload(knownFacts),
  };
  if (isValidUUID(sessionId)) {
    payload.session_id = sessionId;
  }

  const url = `${API_BASE_URL.replace(/\/$/, '')}/ask/stream`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errText = await response.text();
      let errorMsg = `Server error ${response.status}`;
      try {
        const parsed = JSON.parse(errText);
        errorMsg = formatApiError(parsed, errorMsg);
      } catch {
        errorMsg = errText || errorMsg;
      }
      throw new Error(errorMsg);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by response');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        if (!block.trim()) continue;

        let eventType = 'message';
        let dataStr = '';

        const eventLines = block.split('\n');
        for (const line of eventLines) {
          if (line.startsWith('event:')) {
            eventType = line.replace('event:', '').trim();
          } else if (line.startsWith('data:')) {
            dataStr = line.replace('data:', '').trim();
          }
        }

        if (dataStr) {
          try {
            const parsedData = JSON.parse(dataStr);
            if (onEvent) {
              onEvent({ type: eventType, data: parsedData });
            }
          } catch (e) {
            console.error('Failed to parse SSE data JSON:', dataStr, e);
          }
        }
      }
    }

    if (onComplete) onComplete();
  } catch (err) {
    if (onError) onError(err);
  }
}

function cleanScenarioPayload(raw) {
  if (!raw || typeof raw !== 'object') return {};
  const clean = {};
  for (const [k, v] of Object.entries(raw)) {
    if (v !== undefined && v !== null && v !== '') {
      clean[k] = v;
    }
  }
  return clean;
}

export default apiClient;

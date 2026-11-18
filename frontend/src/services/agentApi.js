import { API_BASE_URL } from './apiBase.js';
import { getApiToken } from './authToken.js';

/** Stream the LangChain agent. Browser receives only safe lifecycle metadata and text chunks. */
export async function streamAgentAssistant({ message, sessionId = null, onEvent, onError, onComplete, signal }) {
  const payload = { message };
  if (sessionId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(sessionId)) payload.session_id = sessionId;
  try {
    const token = await getApiToken();
    const response = await fetch(`${API_BASE_URL.replace(/\/$/, '')}/agent/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream', Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload), signal,
    });
    if (!response.ok) {
      const body = await response.text();
      let messageText = `Agent request failed (${response.status})`;
      try { const parsed = JSON.parse(body); messageText = parsed.detail || parsed.message || messageText; } catch { if (body) messageText = body; }
      throw new Error(messageText);
    }
    if (!response.body) throw new Error('Streaming is not supported by this browser.');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    const dispatch = (block) => {
      let type = 'message'; let data = '';
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith('event:')) type = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
      }
      if (data) { try { onEvent?.({ type, data: JSON.parse(data) }); } catch (error) { console.warn('Invalid agent SSE event', error); } }
    };
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() || '';
      blocks.forEach(dispatch);
    }
    buffer += decoder.decode();
    if (buffer.trim()) dispatch(buffer);
    onComplete?.();
  } catch (error) {
    if (error.name !== 'AbortError') onError?.(error);
  }
}

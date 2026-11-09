import express from 'express';
import path from 'path';
import 'dotenv/config';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
// const BACKEND_BASE = process.env.VITE_API_BASE_URL || 'https://flight-disruption-recovery.onrender.com';
const BACKEND_BASE =process.env.BACKEND_URL || 'http://127.0.0.1:8000';

app.use(express.json());

// Proxy all /api routes to the upstream FastAPI backend
app.all('/api/*', async (req, res) => {
  const targetPath = req.originalUrl.replace(/^\/api/, '');
  const targetUrl = `${BACKEND_BASE.replace(/\/$/, '')}${targetPath}`;

  // If this is the SSE streaming endpoint, handle as stream
  if (targetPath.startsWith('/ask/stream')) {
    try {
      const upstreamRes = await fetch(targetUrl, {
        method: req.method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'User-Agent': 'FlightGuard-Frontend/1.0',
        },
        body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
      });

      if (!upstreamRes.ok) {
        const errorText = await upstreamRes.text();
        res.status(upstreamRes.status);
        res.setHeader('Content-Type', 'application/json');
        return res.send(errorText);
      }

      res.status(upstreamRes.status);
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.setHeader('X-Accel-Buffering', 'no');

      if (!upstreamRes.body) {
        return res.end();
      }

      // Read Web Stream and pipe to express response
      const reader = upstreamRes.body.getReader();
      const pump = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              res.end();
              break;
            }
            res.write(Buffer.from(value));
          }
        } catch (err) {
          console.error('SSE Stream pump error:', err);
          res.end();
        }
      };
      return pump();
    } catch (err: any) {
      console.error('SSE Proxy error:', err);
      return res.status(502).json({ error: 'SSE upstream connection failed', detail: err.message });
    }
  }

  // Standard JSON proxy
  try {
    const upstreamRes = await fetch(targetUrl, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FlightGuard-Frontend/1.0',
      },
      body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
    });

    const contentType = upstreamRes.headers.get('content-type') || '';
    res.status(upstreamRes.status);

    if (contentType.includes('application/json')) {
      const data = await upstreamRes.json();
      return res.json(data);
    } else {
      const text = await upstreamRes.text();
      return res.send(text);
    }
  } catch (err: any) {
    console.error(`Proxy error for ${targetUrl}:`, err);
    return res.status(502).json({
      error: 'Upstream gateway error',
      message: err.message,
    });
  }
});

async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: process.env.DISABLE_HMR !== 'true',
      },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, () => {
    console.log(`FlightGuard Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();

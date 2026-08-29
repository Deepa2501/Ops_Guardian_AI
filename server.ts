import express from 'express';
import fs from 'fs';
import path from 'path';
import http from 'http';
import { spawn, ChildProcess } from 'child_process';
import { createServer as createViteServer } from 'vite';

const PORT = parseInt(process.env.PORT || '3000', 10);
const PYTHON_PORT = parseInt(process.env.PYTHON_PORT || '8001', 10);
const localPythonBin = process.platform === 'win32'
  ? path.join(process.cwd(), 'venv', 'Scripts', 'python.exe')
  : path.join(process.cwd(), 'venv', 'bin', 'python');
const PYTHON_BIN = process.env.PYTHON_BIN || (fs.existsSync(localPythonBin) ? localPythonBin : 'python');
const HEALTH_CHECK_MAX_RETRIES = 40;
const HEALTH_CHECK_INTERVAL_MS = 1500;

let pythonProcess: ChildProcess | null = null;
let backendReady = false;

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function waitForBackend(): Promise<boolean> {
  console.log(`[Server] Waiting for Python backend to become healthy on port ${PYTHON_PORT}...`);
  for (let attempt = 1; attempt <= HEALTH_CHECK_MAX_RETRIES; attempt++) {
    try {
      await new Promise<void>((resolve, reject) => {
        const req = http.get(
          { hostname: '127.0.0.1', port: PYTHON_PORT, path: '/api/health', timeout: 2000 },
          (res) => {
            let body = '';
            res.on('data', (chunk) => (body += chunk));
            res.on('end', () => {
              if (res.statusCode === 200) resolve();
              else reject(new Error(`Status ${res.statusCode}`));
            });
          }
        );
        req.on('error', reject);
        req.on('timeout', () => { req.destroy(); reject(new Error('timeout')); });
      });
      console.log(`[Server] ✅ Python backend is healthy (attempt ${attempt}/${HEALTH_CHECK_MAX_RETRIES})`);
      return true;
    } catch {
      if (attempt < HEALTH_CHECK_MAX_RETRIES) {
        process.stdout.write(`\r[Server] Waiting for backend... (${attempt}/${HEALTH_CHECK_MAX_RETRIES})`);
        await sleep(HEALTH_CHECK_INTERVAL_MS);
      }
    }
  }
  console.error(`\n[Server] ⚠️  Backend did not become healthy after ${HEALTH_CHECK_MAX_RETRIES} attempts. Continuing anyway.`);
  return false;
}

function startPythonBackend() {
  // Portable: use `python -m uvicorn` which works on all platforms
  // Falls back gracefully if PYTHON_BIN is set to a full path
  const args = [
    '-m', 'uvicorn',
    'python.app:app',
    '--host', '127.0.0.1',
    '--port', `${PYTHON_PORT}`,
    '--log-level', 'info',
  ];

  console.log(`[Server] Starting Python FastAPI backend: ${PYTHON_BIN} ${args.join(' ')}`);
  
  pythonProcess = spawn(PYTHON_BIN, args, {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PYTHONPATH: process.cwd(),
      PYTHONUNBUFFERED: '1',
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  pythonProcess.stdout?.on('data', (data) => {
    const msg = data.toString().trim();
    if (msg) console.log(`[Python] ${msg}`);
  });

  pythonProcess.stderr?.on('data', (data) => {
    const msg = data.toString().trim();
    if (msg) console.log(`[Python] ${msg}`);  // uvicorn logs go to stderr
  });

  pythonProcess.on('exit', (code, signal) => {
    console.log(`[Python] Process exited (code=${code}, signal=${signal})`);
    backendReady = false;
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error(`[Python] Failed to start: ${err.message}`);
    console.error(`[Python] Make sure Python is installed and accessible as: ${PYTHON_BIN}`);
    console.error(`[Python] You can override with: PYTHON_BIN=/path/to/python npm run dev`);
  });
}

// ── Graceful cleanup ──────────────────────────────────────────────────────────

function shutdown(signal: string) {
  console.log(`\n[Server] Received ${signal}. Shutting down...`);
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    // Give it 3s to die gracefully, then force-kill
    setTimeout(() => {
      if (pythonProcess) pythonProcess.kill('SIGKILL');
    }, 3000);
  }
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('exit', () => { if (pythonProcess) pythonProcess.kill(); });

// ── Main server ───────────────────────────────────────────────────────────────

async function startServer() {
  // 1. Start Python backend subprocess
  startPythonBackend();

  // 2. Wait for it to be healthy before serving (non-blocking — frontend still loads)
  waitForBackend().then((ready) => {
    backendReady = ready;
    if (ready) {
      console.log(`[Server] 🚀 OpsGuardian AI + ArmorIQ is fully operational`);
    }
  });

  const app = express();

  // ── Request ID middleware ──
  app.use((req, _res, next) => {
    (req as any).requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    next();
  });

  // ── API proxy to FastAPI backend ──
  app.use('/api', (req, res) => {
    const options: http.RequestOptions = {
      hostname: '127.0.0.1',
      port: PYTHON_PORT,
      path: req.originalUrl,
      method: req.method,
      headers: {
        ...req.headers,
        host: `127.0.0.1:${PYTHON_PORT}`,
      },
    };

    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
      proxyRes.pipe(res, { end: true });
    });

    proxyReq.on('error', (err) => {
      console.error(`[Proxy Error] ${(req as any).requestId} ${req.method} ${req.url}: ${err.message}`);
      if (!res.headersSent) {
        if (!backendReady) {
          res.status(503).json({
            error: 'Service Unavailable',
            message: 'Python backend is starting up. Please retry in a few seconds.',
            requestId: (req as any).requestId,
          });
        } else {
          res.status(502).json({
            error: 'Bad Gateway',
            message: 'Python backend is temporarily unavailable.',
            details: err.message,
            requestId: (req as any).requestId,
          });
        }
      }
    });

    req.pipe(proxyReq, { end: true });
  });

  // ── Frontend: Vite dev server or static dist ──
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[Server] 🌐 OpsGuardian full-stack server running on http://0.0.0.0:${PORT}`);
    console.log(`[Server]    Python backend: http://127.0.0.1:${PYTHON_PORT}`);
    console.log(`[Server]    PYTHON_BIN: ${PYTHON_BIN}`);
    console.log(`[Server]    AI_PROVIDER: ${process.env.AI_PROVIDER || 'deterministic (default)'}`);
    console.log(`[Server]    ARMORIQ_MODE: ${process.env.ARMORIQ_MODE || 'mock (default)'}`);
  });
}

startServer().catch((err) => {
  console.error('[Server Error]', err);
  process.exit(1);
});

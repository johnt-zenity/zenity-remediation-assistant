import express from 'express';
import { fileURLToPath } from 'node:url';
import { loadConfig, browserConfig } from './config.mjs';
import { createReviewerAuth } from './auth.mjs';
import { lookup, checkLookup } from './lookup.mjs';
import { createReviewClient } from '../../copilot/web/client.js';

const assets = fileURLToPath(new URL('./public/', import.meta.url));
const bearer = value => /^Bearer ([A-Za-z0-9_.~-]{1,16384})$/.exec(value || '')?.[1];
export function createApp(config, dependencies = {}) {
  const authorize = dependencies.authorize || createReviewerAuth(config);
  const retrieve = dependencies.lookup || lookup;
  const invoke = dependencies.review || createReviewClient(config);
  let active = 0;
  // nosemgrep: javascript.express.security.audit.express-check-csurf-middleware-usage.express-check-csurf-middleware-usage -- Exact configured Origin and Fetch Metadata are checked on /plan; signed bearer tokens authenticate every review. No cookie-authenticated mutation exists.
  const app = express();
  app.disable('x-powered-by');
  app.use((_req, res, next) => {
    res.set('X-Content-Type-Options', 'nosniff');
    res.set('Cache-Control', 'no-store');
    res.set('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self' https://login.microsoftonline.com; frame-src https://login.microsoftonline.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
    next();
  });
  app.get('/healthz', (_req, res) => res.json({ ok: true }));
  app.get('/agent-config.json', (_req, res) => res.json(browserConfig(config)));
  app.post('/plan', async (req, res, next) => {
    if (req.get('Origin') !== config.origin || req.get('Sec-Fetch-Site') !== 'same-origin') {
      res.status(403).json({ error: 'Submit the review from this page.' }); return;
    }
    const token = bearer(req.get('Authorization'));
    if (!token) { res.status(401).json({ error: 'Sign in with Microsoft.' }); return; }
    try { req.reviewer = await authorize(token); }
    catch { res.status(401).json({ error: 'Reviewer access denied.' }); return; }
    if (!req.is('application/json')) { res.status(415).json({ error: 'JSON required.' }); return; }
    next();
  }, express.json({ limit: '8kb' }), async (req, res) => {
    const body = req.body;
    const copilotToken = bearer(req.get('X-Copilot-Authorization'));
    if (!body || Array.isArray(body) || Object.keys(body).length !== 1 ||
        typeof body.violation_id !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(body.violation_id) || !copilotToken) {
      res.status(400).json({ error: 'A valid violation ID and Microsoft sign-in are required.' }); return;
    }
    if (active >= 4) { res.set('Retry-After', '10').status(429).json({ error: 'The assistant is busy. Try again shortly.' }); return; }
    active++;
    let finding, timer;
    try {
      finding = await retrieve(body.violation_id);
      if (finding?.mode !== 'live' || finding.outcome !== 'ok' || finding.context?.violation_id !== body.violation_id ||
          !finding.context.planning_source?.rule || !Array.isArray(finding.context.planning_source.findings)) {
        res.status(502).json({ error: 'Unable to retrieve this violation. Check its ID and access.', code: 'lookup_failed' }); return;
      }
      const answer = await Promise.race([
        invoke({ violation_id: body.violation_id, context: finding.context }, copilotToken),
        new Promise((_resolve, reject) => { timer = setTimeout(() => reject(new Error('Agent timeout')), 150000); }),
      ]);
      if (answer?.source !== 'copilot_studio' || !Array.isArray(answer.messages) || !answer.messages.length ||
          answer.messages.some(message => typeof message !== 'string' || !message.trim())) throw new Error('Invalid agent response');
      res.json({ violation_id: body.violation_id, source: 'copilot_studio', finding, messages: answer.messages });
    } catch {
      res.status(503).json({ error: 'The assistant could not complete this review. Try again.', code: 'review_failed',
        ...(finding?.mode === 'live' && finding.outcome === 'ok' && finding.context?.violation_id === body.violation_id ? { finding } : {}) });
    } finally { clearTimeout(timer); active--; }
  });
  app.use(express.static(assets, { index: 'index.html' }));
  app.use((error, _req, res, _next) => res.status(error.status === 413 ? 413 : 400).json({ error: 'Invalid request.' }));
  return app;
}
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const config = loadConfig();
  await checkLookup();
  const server = createApp(config).listen(Number(process.env.PORT || 8080), '0.0.0.0');
  server.requestTimeout = 180000;
  for (const signal of ['SIGTERM', 'SIGINT']) process.once(signal, () => server.close(() => process.exit(0)));
}

/**
 * Cloudflare Edge Intelligence Grid — Router (Entry Point)
 *
 * Architecture:
 *   ┌──────────────────────────────────────────────────────────────┐
 *   │                    Cloudflare Edge Worker                     │
 *   │                                                              │
 *   │  /healthz          → health check                            │
 *   │  /ingest           → observability event ingestion           │
 *   │  /remediate        → trigger remediation pipeline            │
 *   │  /ledger           → read tamper-evident ledger              │
 *   │  /scrape           → invoke browser-rendering scraper        │
 *   │                                                              │
 *   │  Bindings:                                                   │
 *   │    OBSERVABILITY_STATE  → KV namespace for persistent state  │
 *   │    REMEDIATION_QUEUE    → Queue for async remediation events │
 *   │    EDGE_BROWSER         → Browser Rendering instance         │
 *   │    EDGE_DO              → Durable Object for coordination    │
 *   │    AI_GATEWAY           → Cloudflare AI Gateway              │
 *   └──────────────────────────────────────────────────────────────┘
 *
 * Conforms to C-P-A model from AIdevops.txt:
 *   - Context:  RAG corpus from KV / observability state
 *   - Planning: ReAct loop via AI Gateway inference
 *   - Action:   Enqueue remediation events to Queue → Track B
 *
 * All events are written to a SHA-256 chained tamper-evident ledger
 * stored in KV under `ledger::<date>::<seq>` and in the Durable Object.
 */

import { DurableObject } from 'cloudflare:workers';

// ---------------------------------------------------------------------------
// CORS headers for internal service-to-service communication
// ---------------------------------------------------------------------------
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, X-Reasoning-Ref',
  'Access-Control-Max-Age': '86400',
};

function corsResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json', ...extraHeaders },
  });
}

// ---------------------------------------------------------------------------
// Tamper-Evident Ledger (KV-backed, SHA-256 chained)
// ---------------------------------------------------------------------------
async function buildChainHash(env, prevHash, entry) {
  const payload = (prevHash || '') + JSON.stringify(entry, Object.keys(entry).sort());
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(payload));
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

async function writeLedgerEntry(env, eventType, payload) {
  const date = new Date().toISOString().slice(0, 10);
  const id = crypto.randomUUID();
  const entry = {
    id,
    timestamp: new Date().toISOString(),
    type: eventType,
    payload,
  };

  // Get chain head from KV (last entry hash)
  const lastHashKey = `ledger::chain_head::${date}`;
  const lastHash = await env.OBSERVABILITY_STATE.get(lastHashKey);

  entry.chain_hash = await buildChainHash(env, lastHash, entry);

  // Persist entry and update chain head
  const seq = (parseInt(await env.OBSERVABILITY_STATE.get(`ledger::seq::${date}`)) || 0) + 1;
  await Promise.all([
    env.OBSERVABILITY_STATE.put(`ledger::${date}::${String(seq).padStart(6, '0')}`, JSON.stringify(entry)),
    env.OBSERVABILITY_STATE.put(lastHashKey, entry.chain_hash),
    env.OBSERVABILITY_STATE.put(`ledger::seq::${date}`, String(seq)),
  ]);

  return entry;
}

// ---------------------------------------------------------------------------
// Observability Ingestion Pipeline
// ---------------------------------------------------------------------------
async function ingestEvent(env, body) {
  const { event_type, source, payload, severity, metadata } = body;

  if (!event_type || !source || !payload) {
    return { error: 'Missing required fields: event_type, source, payload' };
  }

  // Classify severity via AI Gateway (if enabled)
  let classification = 'unclassified';
  try {
    const aiResult = await env.AI_GATEWAY.run('@cf/meta/llama-3.3-70b-instruct-fp8-fast', {
      messages: [
        {
          role: 'system',
          content:
            'You are a DevOps observability classifier. Classify the event severity as: critical, high, medium, low, or informational. Respond with only one word.',
        },
        {
          role: 'user',
          content: `Event type: ${event_type}\nSource: ${source}\nPayload: ${JSON.stringify(payload)}\nMetadata: ${JSON.stringify(metadata || {})}`,
        },
      ],
    });
    classification = (aiResult?.response || severity || 'unclassified').toLowerCase().trim();
  } catch {
    classification = severity || 'unclassified';
  }

  // Write to tamper-evident ledger
  const ledgerEntry = await writeLedgerEntry(env, `observability::${event_type}`, {
    source,
    payload,
    severity: classification,
    metadata: metadata || {},
    processing_route: classification === 'critical' ? 'immediate' : classification === 'high' ? 'priority' : 'standard',
  });

  // For critical/high events, enqueue remediation to Track B via Queue
  if (classification === 'critical' || classification === 'high') {
    await env.REMEDIATION_QUEUE.send({
      event_id: ledgerEntry.id,
      chain_hash: ledgerEntry.chain_hash,
      event_type,
      source,
      payload,
      severity: classification,
      reasoning_log_ref: ledgerEntry.chain_hash,
      enqueued_at: new Date().toISOString(),
      target_track_b_action: {
        route: classification === 'critical' ? '/execute/auto-remediate' : '/execute/diagnose',
        timeout_seconds: classification === 'critical' ? 15 : 30,
      },
    });
  }

  // Update state snapshot in Durable Object for real-time dashboard
  const doId = env.EDGE_DO.idFromName('intelligence-grid');
  const doStub = env.EDGE_DO.get(doId);
  await doStub.fetch(
    new Request('https://internal/state/update', {
      method: 'POST',
      body: JSON.stringify({ event_type, source, severity: classification, ledger_ref: ledgerEntry.id }),
    })
  );

  return {
    status: 'ingested',
    ledger_id: ledgerEntry.id,
    chain_hash: ledgerEntry.chain_hash,
    classification,
    remediated: classification === 'critical' || classification === 'high',
  };
}

// ---------------------------------------------------------------------------
// Remediation Pipeline Trigger
// ---------------------------------------------------------------------------
async function triggerRemediation(env, body) {
  const { tool, args, reasoning_log_ref, source } = body;

  if (!tool || !reasoning_log_ref) {
    return { error: 'Missing required fields: tool, reasoning_log_ref' };
  }

  const ledgerEntry = await writeLedgerEntry(env, 'remediation_trigger', {
    tool,
    args: args || [],
    reasoning_log_ref,
    source: source || 'cloudflare-edge',
  });

  // Enqueue to the remediation-events queue for Track B consumption
  await env.REMEDIATION_QUEUE.send({
    event_id: ledgerEntry.id,
    chain_hash: ledgerEntry.chain_hash,
    tool,
    args: args || [],
    reasoning_log_ref,
    enqueued_at: new Date().toISOString(),
  });

  return {
    status: 'enqueued',
    ledger_id: ledgerEntry.id,
    chain_hash: ledgerEntry.chain_hash,
  };
}

// ---------------------------------------------------------------------------
// Ledger Query
// ---------------------------------------------------------------------------
async function queryLedger(env, limit = 50) {
  const date = new Date().toISOString().slice(0, 10);
  const entries = [];
  const maxSeq = parseInt(await env.OBSERVABILITY_STATE.get(`ledger::seq::${date}`)) || 0;

  const startSeq = Math.max(1, maxSeq - limit + 1);
  const keys = [];
  for (let i = startSeq; i <= maxSeq; i++) {
    keys.push(`ledger::${date}::${String(i).padStart(6, '0')}`);
  }

  const results = await Promise.all(keys.map((k) => env.OBSERVABILITY_STATE.get(k)));
  for (const raw of results) {
    if (raw) {
      try {
        entries.push(JSON.parse(raw));
      } catch {
        // skip corrupt entries
      }
    }
  }

  return { entries, count: entries.length, date };
}

// ---------------------------------------------------------------------------
// Broker: invoke scraper.js via Browser Rendering
// ---------------------------------------------------------------------------
async function invokeScraper(env, target) {
  try {
    // Use the EDGE_BROWSER binding to start a headless session
    const browser = await env.EDGE_BROWSER.launch();
    const page = await browser.newPage();

    await page.goto(target.url || 'http://track-a-control-loop:8080/healthz', {
      waitUntil: 'networkidle0',
      timeout: 15000,
    });

    const content = await page.content();
    const metrics = await page.evaluate(() => {
      const body = document.body.innerText;
      let parsed;
      try {
        parsed = JSON.parse(body);
      } catch {
        parsed = { raw: body };
      }
      return {
        url: window.location.href,
        status_code: 200,
        title: document.title,
        body: parsed,
        timestamp: new Date().toISOString(),
      };
    });

    await browser.close();

    // Write scrape result to ledger
    const ledgerEntry = await writeLedgerEntry(env, 'browser_scrape', {
      target: target.url,
      metrics,
      scraper: 'cloudflare-edge-browser',
    });

    return {
      status: 'scraped',
      ledger_id: ledgerEntry.id,
      metrics,
    };
  } catch (err) {
    await writeLedgerEntry(env, 'scrape_error', {
      target: target?.url || 'unknown',
      error: err.message,
    });
    return { error: `Browser scrape failed: ${err.message}` };
  }
}

// ---------------------------------------------------------------------------
// Durable Object — Intelligence Grid State Coordinator
// ---------------------------------------------------------------------------
export class EdgeIntelligenceDO extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx = ctx;
    this.env = env;
    // In-memory state snapshot (ephemeral, rebuilt on cold start from KV)
    this.state = {
      event_counts: {},
      severity_counts: {},
      active_remediations: [],
      last_updated: null,
    };
  }

  async fetch(request) {
    const url = new URL(request.url);

    // Rebuild state from KV on cold start
    if (!this.state.last_updated) {
      await this.rebuildState();
    }

    switch (url.pathname) {
      case '/state/update':
        return this.handleStateUpdate(request);
      case '/state/snapshot':
        return this.handleStateSnapshot();
      case '/state/reset':
        return this.handleStateReset();
      default:
        return corsResponse({ error: 'Unknown DO endpoint' }, 404);
    }
  }

  async rebuildState() {
    const raw = await this.ctx.storage.get('grid_state');
    if (raw) {
      this.state = raw;
    }
    this.state.last_updated = new Date().toISOString();
  }

  async persistState() {
    this.state.last_updated = new Date().toISOString();
    await this.ctx.storage.put('grid_state', this.state);
  }

  async handleStateUpdate(request) {
    const body = await request.json();
    const { event_type, source, severity, ledger_ref } = body;

    // Increment event counts
    this.state.event_counts[event_type] = (this.state.event_counts[event_type] || 0) + 1;
    this.state.event_counts[source] = (this.state.event_counts[source] || 0) + 1;
    this.state.severity_counts[severity] = (this.state.severity_counts[severity] || 0) + 1;

    // Track active remediations
    if (severity === 'critical') {
      this.state.active_remediations.push({
        ledger_ref,
        event_type,
        source,
        severity,
        started_at: new Date().toISOString(),
      });
      // Keep only last 100 active remediations
      if (this.state.active_remediations.length > 100) {
        this.state.active_remediations = this.state.active_remediations.slice(-100);
      }
    }

    await this.persistState();
    return corsResponse({ status: 'updated' });
  }

  async handleStateSnapshot() {
    return corsResponse({
      snapshot: this.state,
      do_id: this.ctx.id.toString(),
    });
  }

  async handleStateReset() {
    this.state = {
      event_counts: {},
      severity_counts: {},
      active_remediations: [],
      last_updated: new Date().toISOString(),
    };
    await this.persistState();
    return corsResponse({ status: 'reset' });
  }
}

// ---------------------------------------------------------------------------
// Main Worker Handler
// ---------------------------------------------------------------------------
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method.toUpperCase();

    // CORS preflight
    if (method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    // Route dispatch
    try {
      switch (url.pathname) {
        // ---- Health Check ----
        case '/healthz':
          return corsResponse({
            status: 'healthy',
            service: 'cloudflare-edge-intelligence-grid',
            version: '0.1.0',
            bindings: {
              kv: !!env.OBSERVABILITY_STATE,
              queue: !!env.REMEDIATION_QUEUE,
              browser: !!env.EDGE_BROWSER,
              ai_gateway: !!env.AI_GATEWAY,
              durable_object: !!env.EDGE_DO,
            },
          });

        // ---- Observability Ingestion ----
        case '/ingest':
          if (method !== 'POST') {
            return corsResponse({ error: 'Method not allowed' }, 405);
          }
          {
            const body = await request.json();
            const result = await ingestEvent(env, body);
            return corsResponse(result, result.error ? 400 : 200);
          }

        // ---- Remediation Trigger ----
        case '/remediate':
          if (method !== 'POST') {
            return corsResponse({ error: 'Method not allowed' }, 405);
          }
          {
            const body = await request.json();
            const result = await triggerRemediation(env, body);
            return corsResponse(result, result.error ? 400 : 200);
          }

        // ---- Ledger Query ----
        case '/ledger':
          if (method !== 'GET') {
            return corsResponse({ error: 'Method not allowed' }, 405);
          }
          {
            const limit = parseInt(url.searchParams.get('limit') || '50');
            const result = await queryLedger(env, limit);
            return corsResponse(result);
          }

        // ---- Browser Scraping ----
        case '/scrape':
          if (method !== 'POST') {
            return corsResponse({ error: 'Method not allowed' }, 405);
          }
          {
            const body = await request.json();
            const result = await invokeScraper(env, body);
            return corsResponse(result, result.error ? 500 : 200);
          }

        // ---- Intelligence Grid State Snapshot (from Durable Object) ----
        case '/state': {
          const doId = env.EDGE_DO.idFromName('intelligence-grid');
          const doStub = env.EDGE_DO.get(doId);
          return doStub.fetch(new Request('https://internal/state/snapshot'));
        }

        // ---- Root / Index ----
        case '/':
          return corsResponse({
            service: 'cloudflare-edge-intelligence-grid',
            version: '0.1.0',
            model: 'C-P-A Edge Intelligence Grid',
            endpoints: {
              '/healthz': 'GET — health check with binding status',
              '/ingest': 'POST — ingest observability event (classification + remediation enqueue)',
              '/remediate': 'POST — trigger remediation pipeline',
              '/ledger': 'GET — query tamper-evident ledger',
              '/scrape': 'POST — invoke browser-rendering scraper',
              '/state': 'GET — intelligence grid state snapshot (Durable Object)',
            },
          });

        default:
          return corsResponse({ error: 'Not found' }, 404);
      }
    } catch (err) {
      // Log the error to KV for post-mortem
      await writeLedgerEntry(env, 'worker_error', {
        path: url.pathname,
        method,
        error: err.message,
        stack: err.stack,
      }).catch(() => {});

      return corsResponse(
        { error: 'Internal server error', detail: err.message },
        500
      );
    }
  },

  /**
   * Queue consumer: processes remediation events and dispatches to Track B.
   * Each batch is processed with idempotency keys to prevent duplicate dispatch.
   */
  async queue(batch, env, ctx) {
    for (const msg of batch.messages) {
      try {
        const { event_id, chain_hash, tool, args, reasoning_log_ref, target_track_b_action } = msg.body;

        // Check idempotency: has this event already been processed?
        const processedKey = `remediation::processed::${event_id}`;
        const alreadyProcessed = await env.OBSERVABILITY_STATE.get(processedKey);
        if (alreadyProcessed) {
          msg.ack();
          continue;
        }

        // Dispatch to Track B actuator with the original reasoning ref
        const trackBUrl = env.TRACK_B_URL || 'http://track-b-actuator:8081';
        const response = await fetch(`${trackBUrl}/execute`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            tool: tool || 'kubectl get pods',
            args: args || [],
            reasoning_log_ref: reasoning_log_ref || chain_hash,
          }),
        });

        const result = response.ok ? await response.json() : { error: `Track B returned ${response.status}` };

        // Mark as processed
        await env.OBSERVABILITY_STATE.put(processedKey, JSON.stringify({
          processed_at: new Date().toISOString(),
          event_id,
          track_b_response: result,
        }), { expirationTtl: 86400 * 7 }); // 7-day idempotency window

        // Write remediation result to ledger
        await writeLedgerEntry(env, 'remediation_result', {
          event_id,
          chain_hash,
          tool,
          result,
          track_b_status: response.status,
        });

        msg.ack();
      } catch (err) {
        // Record error but ack to avoid poison-pill infinite retry
        await writeLedgerEntry(env, 'queue_consumer_error', {
          error: err.message,
          event_id: msg.body?.event_id,
        }).catch(() => {});
        msg.ack();
      }
    }
  },
};

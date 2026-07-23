/**
 * _worker.js — Cloudflare Pages Advanced Mode
 *
 * Handles:
 *   POST /api/submit-scrape → proxy to AI Gateway
 *   Everything else → static assets
 */

const AI_GATEWAY_URL =
  'https://gateway.ai.cloudflare.com/v1/197a5689d9c0df2855f017dcbfc59f4a/openclaw-gateway/compat/chat/completions';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    /* ── API route: /api/submit-scrape ── */
    if (url.pathname === '/api/submit-scrape' && request.method === 'POST') {
      return handleSubmitScrape(request);
    }

    /* ── CORS preflight for API routes ── */
    if (url.pathname.startsWith('/api/') && request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    /* ── Everything else: serve static assets ── */
    return env.ASSETS.fetch(request);
  },
};

async function handleSubmitScrape(request) {
  const origin = request.headers.get('origin') || '*';
  const corsHeaders = {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  /* Parse incoming JSON */
  let payload;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse(
      { success: false, error: 'Invalid JSON body.' },
      400,
      corsHeaders
    );
  }

  const { target_url, context_label } = payload || {};

  if (!target_url || typeof target_url !== 'string') {
    return jsonResponse(
      { success: false, error: 'Missing or invalid target_url.' },
      400,
      corsHeaders
    );
  }

  if (!context_label || typeof context_label !== 'string') {
    return jsonResponse(
      { success: false, error: 'Missing or invalid context_label.' },
      400,
      corsHeaders
    );
  }

  /* Build outbound request to AI Gateway */
  const gatewayPayload = {
    model: 'openviking-ingest',
    messages: [
      {
        role: 'system',
        content: `Ingest URL into RAG pipeline. Context: ${context_label}`,
      },
      {
        role: 'user',
        content: target_url,
      },
    ],
    metadata: {
      context_label: context_label,
      submitted_at: new Date().toISOString(),
      source: 'openviking-web-ingest-portal',
    },
  };

  const headers = new Headers({
    'Content-Type': 'application/json',
    'X-Agent-ID': 'openviking-web-ingest-portal',
    'X-Task-Type': 'critical-engineering',
  });

  /* Forward to AI Gateway */
  let gatewayRes;
  try {
    gatewayRes = await fetch(AI_GATEWAY_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify(gatewayPayload),
    });
  } catch (err) {
    return jsonResponse(
      { success: false, error: 'Gateway unreachable: ' + err.message },
      502,
      corsHeaders
    );
  }

  /* Handle gateway response */
  if (gatewayRes.ok) {
    let gatewayBody;
    try {
      gatewayBody = await gatewayRes.json();
    } catch {
      gatewayBody = null;
    }

    return jsonResponse(
      {
        success: true,
        message: `URL accepted for ingestion. Context: ${context_label}`,
        gateway_status: gatewayRes.status,
        reference: gatewayBody?.id || null,
      },
      200,
      corsHeaders
    );
  }

  /* Gateway returned non-2xx */
  let errorDetail;
  try {
    const errBody = await gatewayRes.json();
    errorDetail = errBody?.error?.message || JSON.stringify(errBody);
  } catch {
    errorDetail = 'Gateway returned HTTP ' + gatewayRes.status;
  }

  return jsonResponse(
    {
      success: false,
      error:
        'Gateway rejected request (HTTP ' +
        gatewayRes.status +
        '): ' +
        errorDetail,
      context_label,
    },
    gatewayRes.status,
    corsHeaders
  );
}

function jsonResponse(body, status, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...extraHeaders,
    },
  });
}

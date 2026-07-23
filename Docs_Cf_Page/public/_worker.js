/**
 * _worker.js — Cloudflare Pages Advanced Mode
 *
 * Handles:
 *   POST /api/submit-scrape → proxy to AI Gateway (URL or Text mode)
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

  const { target_url, text_content, context_label } = payload || {};

  if (!context_label || typeof context_label !== 'string') {
    return jsonResponse(
      { success: false, error: 'Missing or invalid context_label.' },
      400,
      corsHeaders
    );
  }

  let gatewayPayload;

  /* ── URL mode ── */
  if (target_url && typeof target_url === 'string') {
    gatewayPayload = {
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
        ingest_type: 'url',
        context_label: context_label,
        submitted_at: new Date().toISOString(),
        source: 'openviking-web-ingest-portal',
      },
    };
  }

  /* ── Text mode ── */
  else if (text_content && typeof text_content === 'string') {
    const markdown = convertToMarkdown(text_content, context_label);

    gatewayPayload = {
      model: 'openviking-ingest',
      messages: [
        {
          role: 'system',
          content: `Ingest document into RAG pipeline. Context: ${context_label}. Format: Markdown`,
        },
        {
          role: 'user',
          content: markdown,
        },
      ],
      metadata: {
        ingest_type: 'text',
        context_label: context_label,
        submitted_at: new Date().toISOString(),
        source: 'openviking-web-ingest-portal',
        original_format: 'plain_text',
        converted_format: 'markdown',
      },
    };
  }

  else {
    return jsonResponse(
      { success: false, error: 'Missing or invalid submission. Provide either target_url or text_content.' },
      400,
      corsHeaders
    );
  }

  /* Build outbound headers */
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

    const isUrl = target_url ? true : false;
    return jsonResponse(
      {
        success: true,
        message: `${isUrl ? 'URL' : 'Text document'} accepted for ingestion. Context: ${context_label}`,
        gateway_status: gatewayRes.status,
        reference: gatewayBody?.id || null,
        ingest_type: isUrl ? 'url' : 'text',
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

/**
 * Convert plain text to Markdown format.
 * Wraps the content in a structured markdown document with frontmatter.
 */
function convertToMarkdown(text, category) {
  const timestamp = new Date().toISOString();
  const title = category.replace(/_/g, ' ');

  const escapedText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return `---
title: "${title}"
category: ${category}
ingested_at: ${timestamp}
source: openviking-web-ingest-portal
format: markdown
---

# ${title}

${escapedText}
`;
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

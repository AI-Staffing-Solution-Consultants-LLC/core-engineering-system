/**
 * Sheryl Agent Responses Proxy — Pages Function
 *
 * GET /api/sheryl/responses
 * Proxies requests to Sheryl's /dashboard/last-responses endpoint.
 * Returns JSON array: [{ agent, timestamp, query, response, ambiguous }, ...] (max 5)
 *
 * Falls back to placeholder data if SHERYL_URL env var is not configured or
 * Sheryl endpoint is unreachable.
 */

const PLACEHOLDER_RESPONSES = [
  {
    agent: 'Sheryl — Strategy',
    timestamp: '2026-07-28T14:32:10Z',
    query: 'Analyze current system health and recommend optimizations for the Mesh deployment.',
    response: 'System health is nominal across all 8 services. Recommend scaling Track A memory to 512Mi to handle increased RAG corpus size. No critical alerts.',
    ambiguous: false,
  },
  {
    agent: 'Mary — Monitoring',
    timestamp: '2026-07-28T14:31:45Z',
    query: 'Check for any anomalous patterns in the last 4 hours of telemetry.',
    response: 'Detected slight latency increase in Track B actuator (P99 180ms → 210ms). Likely caused by increased tool execution queue depth. Not critical.',
    ambiguous: false,
  },
  {
    agent: 'Roy — Predictions',
    timestamp: '2026-07-28T14:30:22Z',
    query: 'Predict resource utilization for next 24 hours based on current trends.',
    response: 'Projected CPU at 55-62%, memory at 3.1-3.4 GB. Within free tier limits. No scaling action required.',
    ambiguous: false,
  },
  {
    agent: 'Connie — Code Analysis',
    timestamp: '2026-07-28T14:29:58Z',
    query: 'Review recent commit patterns for potential security or performance regressions.',
    response: 'Two commits flagged for review: dependency bump could introduce CVE-2026-XXXX if not pinned; regex in track-a/main.py line 312 may ReDoS under large corpus.',
    ambiguous: true,
  },
  {
    agent: 'Data Remediation Engine',
    timestamp: '2026-07-28T14:28:15Z',
    query: 'Check for data anomalies in the last remediation cycle.',
    response: '12 anomalies detected, 11 auto-resolved. 1 pending: ledger entry hash mismatch in track-b/ledger-2026-07-28.jsonl entry #847. Manual audit recommended.',
    ambiguous: false,
  },
];

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };
}

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  if (request.method !== 'GET') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: corsHeaders() }
    );
  }

  const sherylUrl = env.SHERYL_URL;

  if (!sherylUrl) {
    return new Response(
      JSON.stringify(PLACEHOLDER_RESPONSES),
      { status: 200, headers: corsHeaders() }
    );
  }

  try {
    const targetUrl = `${sherylUrl.replace(/\/$/, '')}/dashboard/last-responses`;
    const sherylResponse = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!sherylResponse.ok) {
      console.error(
        `[Sheryl Proxy] Sheryl endpoint returned ${sherylResponse.status}`
      );
      return new Response(
        JSON.stringify(PLACEHOLDER_RESPONSES),
        { status: 200, headers: corsHeaders() }
      );
    }

    const data = await sherylResponse.json();

    if (!Array.isArray(data)) {
      console.error('[Sheryl Proxy] Unexpected response format from Sheryl');
      return new Response(
        JSON.stringify(PLACEHOLDER_RESPONSES),
        { status: 200, headers: corsHeaders() }
      );
    }

    return new Response(
      JSON.stringify(data.slice(0, 5)),
      { status: 200, headers: corsHeaders() }
    );
  } catch (err) {
    console.error('[Sheryl Proxy] Network error reaching Sheryl:', err.message);
    return new Response(
      JSON.stringify(PLACEHOLDER_RESPONSES),
      { status: 200, headers: corsHeaders() }
    );
  }
}

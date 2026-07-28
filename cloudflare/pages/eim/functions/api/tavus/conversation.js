/**
 * Tavus CVI Conversation — Pages Function
 * ========================================
 * Proxies Tavus Conversational Video Interface REST API calls.
 * The TAVUS_API_KEY is stored server-side via env vars — NEVER returned to client.
 *
 * POST /api/tavus/conversation
 * Body: {} (optional overrides: { persona_id, replica_id })
 * Response: { conversation_url: "https://...", conversation_id: "...", status: "..." }
 *
 * Error responses: 400 (invalid body), 502 (Tavus unreachable), 500 (other errors)
 *
 * Tavus API reference: https://docs.tavus.io/sections/conversational-video-interface/overview-cvi
 */

/* ── Tavus API Configuration ────────────────────────────────────────────── */

const TAVUS_API_BASE = 'https://tavusapi.com/v2';
const TAVUS_CONVERSATION_ENDPOINT = `${TAVUS_API_BASE}/conversations`;

/* ── CORS Helpers ───────────────────────────────────────────────────────── */

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Content-Type': 'application/json',
  };
}

/* ── Main Handler ───────────────────────────────────────────────────────── */

export async function onRequest(context) {
  const { request, env } = context;

  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }

  // Only POST is allowed
  if (request.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'Method not allowed' }),
      { status: 405, headers: corsHeaders() }
    );
  }

  // Read API key from environment — NEVER hardcoded
  const apiKey = env.TAVUS_API_KEY;
  if (!apiKey) {
    console.error('[Tavus CVI] TAVUS_API_KEY env var is not configured.');
    return new Response(
      JSON.stringify({ error: 'Tavus API key not configured on server' }),
      { status: 500, headers: corsHeaders() }
    );
  }

  // Parse request body for optional overrides
  let body;
  try {
    body = await request.json();
  } catch {
    body = {};
  }

  const { persona_id, replica_id, ...extraOpts } = body;

  // Build Tavus conversation request payload
  const tavusPayload = {};

  if (persona_id) {
    tavusPayload.persona_id = persona_id;
  } else if (env.TAVUS_PERSONA_ID) {
    tavusPayload.persona_id = env.TAVUS_PERSONA_ID;
  }

  if (replica_id) {
    tavusPayload.replica_id = replica_id;
  } else if (env.TAVUS_REPLICA_ID) {
    tavusPayload.replica_id = env.TAVUS_REPLICA_ID;
  }

  // Merge any additional options from client request
  Object.assign(tavusPayload, extraOpts);

  // Fire Tavus API
  let tavusResponse;
  try {
    tavusResponse = await fetch(TAVUS_CONVERSATION_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
      },
      body: JSON.stringify(tavusPayload),
    });
  } catch (err) {
    console.error('[Tavus CVI] Network error reaching Tavus API:', err.message);
    return new Response(
      JSON.stringify({ error: 'Tavus API unreachable', detail: err.message }),
      { status: 502, headers: corsHeaders() }
    );
  }

  // Parse Tavus response
  let tavusData;
  try {
    tavusData = await tavusResponse.json();
  } catch {
    const rawText = await tavusResponse.text();
    console.error('[Tavus CVI] Non-JSON response from Tavus:', rawText.slice(0, 500));
    return new Response(
      JSON.stringify({ error: 'Invalid response from Tavus API' }),
      { status: 502, headers: corsHeaders() }
    );
  }

  // If Tavus returned an error
  if (!tavusResponse.ok) {
    console.error('[Tavus CVI] Tavus API error:', tavusResponse.status, JSON.stringify(tavusData));
    return new Response(
      JSON.stringify({
        error: 'Tavus API returned an error',
        status: tavusResponse.status,
        detail: tavusData,
      }),
      { status: 502, headers: corsHeaders() }
    );
  }

  // Success — return the conversation details to client
  return new Response(
    JSON.stringify({
      conversation_url: tavusData.conversation_url,
      conversation_id: tavusData.conversation_id,
      status: tavusData.status,
      created_at: tavusData.created_at,
    }),
    { status: 200, headers: corsHeaders() }
  );
}

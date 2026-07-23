/**
 * OpenViking Ingest Portal — Cloudflare Worker
 *
 * Environments: dev, staging, production
 * Serves static HTML + proxies API requests to AI Gateway
 */

const AI_GATEWAY_URL =
  'https://gateway.ai.cloudflare.com/v1/197a5689d9c0df2855f017dcbfc59f4a/openclaw-gateway/compat/chat/completions';

/* Inlined frontend HTML */
const HTML_CONTENT = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenViking Memory Mesh — Ingest Portal</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0b0e14; --surface: #141820; --border: #1e2530;
      --accent: #38bdf8; --accent-hover: #7dd3fc;
      --text: #e2e8f0; --text-muted: #94a3b8;
      --success: #22c55e; --error: #ef4444; --radius: 8px;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      background: var(--bg); color: var(--text);
      min-height: 100vh; display: flex; align-items: center; justify-content: center;
      padding: 1.5rem;
    }
    .card {
      background: var(--surface); border: 1px solid var(--border);
      border-radius: 12px; padding: 2.5rem; width: 100%; max-width: 520px;
    }
    .logo { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.15em;
      color: var(--accent); margin-bottom: 0.25rem; }
    h1 { font-size: 1.4rem; font-weight: 600; margin-bottom: 0.25rem; }
    .subtitle { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1.75rem; }
    label { display: block; font-size: 0.8rem; font-weight: 500;
      color: var(--text-muted); margin-bottom: 0.35rem; }
    input[type="url"], select, textarea {
      width: 100%; padding: 0.6rem 0.75rem; background: var(--bg);
      border: 1px solid var(--border); border-radius: var(--radius);
      color: var(--text); font-size: 0.9rem; outline: none;
      transition: border-color 0.15s; font-family: inherit;
    }
    input:focus, select:focus, textarea:focus { border-color: var(--accent); }
    input::placeholder, textarea::placeholder { color: #475569; }
    textarea { min-height: 140px; resize: vertical; line-height: 1.5; }
    .field { margin-bottom: 1.1rem; }
    select { appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2394a3b8'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 0.75rem center;
      padding-right: 2rem; cursor: pointer;
    }
    select option { background: var(--surface); color: var(--text); }
    .mode-toggle { display: flex; gap: 0.5rem; margin-bottom: 1.1rem; }
    .mode-btn { flex: 1; padding: 0.5rem; background: var(--bg);
      border: 1px solid var(--border); border-radius: var(--radius);
      color: var(--text-muted); font-size: 0.85rem; font-weight: 500;
      cursor: pointer; transition: all 0.15s;
    }
    .mode-btn.active { background: rgba(56,189,248,0.15);
      border-color: var(--accent); color: var(--accent); }
    .mode-btn:hover:not(.active) { border-color: #334155; color: var(--text); }
    .hidden { display: none !important; }
    .submit-btn { width: 100%; padding: 0.7rem; margin-top: 0.5rem;
      background: var(--accent); color: #0b0e14; border: none;
      border-radius: var(--radius); font-size: 0.9rem; font-weight: 600;
      cursor: pointer; transition: background 0.15s, opacity 0.15s;
    }
    .submit-btn:hover:not(:disabled) { background: var(--accent-hover); }
    .submit-btn:disabled { opacity: 0.55; cursor: not-allowed; }
    .spinner { display: none; width: 18px; height: 18px;
      border: 2.5px solid var(--bg); border-top-color: transparent;
      border-radius: 50%; animation: spin 0.6s linear infinite; margin: 0 auto;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .status { margin-top: 1rem; padding: 0.7rem 0.85rem;
      border-radius: var(--radius); font-size: 0.82rem; line-height: 1.45;
      display: none; word-break: break-word;
    }
    .status.ok { display: block; background: rgba(34,197,94,0.1);
      border: 1px solid rgba(34,197,94,0.3); color: var(--success); }
    .status.err { display: block; background: rgba(239,68,68,0.1);
      border: 1px solid rgba(239,68,68,0.3); color: var(--error); }
    .footer { margin-top: 1.5rem; text-align: center; font-size: 0.72rem; color: #475569; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">OpenViking</div>
    <h1>Memory Mesh Ingest</h1>
    <p class="subtitle">Submit documentation URLs or raw text for RAG ingestion into the OpenViking knowledge pipeline.</p>
    <form id="ingest_form" autocomplete="off">
      <div class="mode-toggle">
        <button type="button" class="mode-btn active" data-mode="url" id="mode_url">URL</button>
        <button type="button" class="mode-btn" data-mode="text" id="mode_text">Text</button>
      </div>
      <div class="field" id="url_field">
        <label for="target_url">Target URL</label>
        <input type="url" id="target_url" name="target_url" placeholder="https://example.com/docs" required>
      </div>
      <div class="field hidden" id="text_field">
        <label for="text_content">Document Text</label>
        <textarea id="text_content" name="text_content" placeholder="Paste or type your documentation text here. It will be converted to Markdown and ingested into the RAG pipeline."></textarea>
        <p style="font-size:0.75rem; color:#475569; margin-top:0.35rem;">The system auto-converts this to .md format before ingestion.</p>
      </div>
      <div class="field">
        <label for="context_label">Category</label>
        <select id="context_label" name="context_label" required>
          <option value="Component_Documentation" selected>Component Documentation</option>
          <option value="OpenCode_Transcripts">OpenCode Transcripts</option>
          <option value="Planned_Concepts">Planned Concepts</option>
        </select>
      </div>
      <button type="submit" class="submit-btn" id="submit_btn">
        <span id="btn_label">Submit to OpenViking Memory Mesh</span>
        <span class="spinner" id="btn_spinner"></span>
      </button>
    </form>
    <div class="status" id="status_box"></div>
    <div class="footer">OpenViking RAG Ingestion Portal · AI Staffing Solutions</div>
  </div>
  <script>
    (function () {
      const form = document.getElementById('ingest_form');
      const btn = document.getElementById('submit_btn');
      const label = document.getElementById('btn_label');
      const spinner = document.getElementById('btn_spinner');
      const status = document.getElementById('status_box');
      const modeUrlBtn = document.getElementById('mode_url');
      const modeTextBtn = document.getElementById('mode_text');
      const urlField = document.getElementById('url_field');
      const textField = document.getElementById('text_field');
      const urlInput = document.getElementById('target_url');
      const textInput = document.getElementById('text_content');
      let currentMode = 'url';
      function setMode(mode) {
        currentMode = mode;
        if (mode === 'url') {
          modeUrlBtn.classList.add('active'); modeTextBtn.classList.remove('active');
          urlField.classList.remove('hidden'); textField.classList.add('hidden');
          urlInput.setAttribute('required', ''); textInput.removeAttribute('required');
        } else {
          modeTextBtn.classList.add('active'); modeUrlBtn.classList.remove('active');
          urlField.classList.add('hidden'); textField.classList.remove('hidden');
          urlInput.removeAttribute('required'); textInput.setAttribute('required', '');
        }
      }
      modeUrlBtn.addEventListener('click', () => setMode('url'));
      modeTextBtn.addEventListener('click', () => setMode('text'));
      function setLoading(on) {
        btn.disabled = on; label.style.display = on ? 'none' : '';
        spinner.style.display = on ? 'block' : 'none';
      }
      function showStatus(type, msg) {
        status.className = 'status ' + type; status.textContent = msg;
      }
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        const contextLabel = document.getElementById('context_label').value;
        let payload;
        if (currentMode === 'url') {
          const targetUrl = urlInput.value.trim();
          if (!targetUrl) return;
          payload = { target_url: targetUrl, context_label: contextLabel };
        } else {
          const textContent = textInput.value.trim();
          if (!textContent) return;
          payload = { text_content: textContent, context_label: contextLabel };
        }
        setLoading(true); status.className = 'status'; status.textContent = '';
        try {
          const res = await fetch('/api/submit-scrape', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (res.ok && data.success) {
            showStatus('ok', '\u2714 ' + (data.message || 'Submission accepted.'));
          } else {
            showStatus('err', '\u2718 ' + (data.error || 'Server returned status ' + res.status));
          }
        } catch (err) {
          showStatus('err', '\u2718 Network error: ' + err.message);
        } finally { setLoading(false); }
      });
    })();
  </script>
</body>
</html>`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    /* Serve frontend HTML */
    if (url.pathname === '/' && request.method === 'GET') {
      return new Response(HTML_CONTENT, {
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      });
    }

    /* API route */
    if (url.pathname === '/api/submit-scrape' && request.method === 'POST') {
      return handleSubmitScrape(request);
    }

    /* CORS preflight */
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

    /* 404 for everything else */
    return new Response('Not Found', { status: 404 });
  },
};

async function handleSubmitScrape(request) {
  const origin = request.headers.get('origin') || '*';
  const corsHeaders = {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  let payload;
  try {
    payload = await request.json();
  } catch {
    return jsonResponse({ success: false, error: 'Invalid JSON body.' }, 400, corsHeaders);
  }

  const { target_url, text_content, context_label } = payload || {};

  if (!context_label || typeof context_label !== 'string') {
    return jsonResponse({ success: false, error: 'Missing or invalid context_label.' }, 400, corsHeaders);
  }

  let gatewayPayload;

  if (target_url && typeof target_url === 'string') {
    gatewayPayload = {
      model: 'openviking-ingest',
      messages: [
        { role: 'system', content: `Ingest URL into RAG pipeline. Context: ${context_label}` },
        { role: 'user', content: target_url },
      ],
      metadata: {
        ingest_type: 'url', context_label,
        submitted_at: new Date().toISOString(),
        source: 'openviking-web-ingest-portal',
      },
    };
  } else if (text_content && typeof text_content === 'string') {
    const markdown = convertToMarkdown(text_content, context_label);
    gatewayPayload = {
      model: 'openviking-ingest',
      messages: [
        { role: 'system', content: `Ingest document into RAG pipeline. Context: ${context_label}. Format: Markdown` },
        { role: 'user', content: markdown },
      ],
      metadata: {
        ingest_type: 'text', context_label,
        submitted_at: new Date().toISOString(),
        source: 'openviking-web-ingest-portal',
        original_format: 'plain_text', converted_format: 'markdown',
      },
    };
  } else {
    return jsonResponse({ success: false, error: 'Missing or invalid submission. Provide either target_url or text_content.' }, 400, corsHeaders);
  }

  const headers = new Headers({
    'Content-Type': 'application/json',
    'X-Agent-ID': 'openviking-web-ingest-portal',
    'X-Task-Type': 'critical-engineering',
  });

  let gatewayRes;
  try {
    gatewayRes = await fetch(AI_GATEWAY_URL, {
      method: 'POST', headers, body: JSON.stringify(gatewayPayload),
    });
  } catch (err) {
    return jsonResponse({ success: false, error: 'Gateway unreachable: ' + err.message }, 502, corsHeaders);
  }

  if (gatewayRes.ok) {
    let gatewayBody;
    try { gatewayBody = await gatewayRes.json(); } catch { gatewayBody = null; }
    const isUrl = target_url ? true : false;
    return jsonResponse({
      success: true,
      message: `${isUrl ? 'URL' : 'Text document'} accepted for ingestion. Context: ${context_label}`,
      gateway_status: gatewayRes.status,
      reference: gatewayBody?.id || null,
      ingest_type: isUrl ? 'url' : 'text',
    }, 200, corsHeaders);
  }

  let errorDetail;
  try {
    const errBody = await gatewayRes.json();
    errorDetail = errBody?.error?.message || JSON.stringify(errBody);
  } catch {
    errorDetail = 'Gateway returned HTTP ' + gatewayRes.status;
  }

  return jsonResponse({
    success: false,
    error: 'Gateway rejected request (HTTP ' + gatewayRes.status + '): ' + errorDetail,
    context_label,
  }, gatewayRes.status, corsHeaders);
}

function convertToMarkdown(text, category) {
  const timestamp = new Date().toISOString();
  const title = category.replace(/_/g, ' ');
  const escapedText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return `---\ntitle: "${title}"\ncategory: ${category}\ningested_at: ${timestamp}\nsource: openviking-web-ingest-portal\nformat: markdown\n---\n\n# ${title}\n\n${escapedText}\n`;
}

function jsonResponse(body, status, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  });
}

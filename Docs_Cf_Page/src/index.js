/**
 * OpenViking RAG System — Cloudflare Worker
 *
 * Full pipeline: URL scrape → text extract → markdown → embeddings → Vectorize storage
 * Semantic search: query → embeddings → vector search → ranked results
 *
 * Environments: dev, staging, production
 */

const EMBED_MODEL = '@cf/google/embeddinggemma-300m';
const VECTORIZE_API = 'https://api.cloudflare.com/client/v4/accounts/197a5689d9c0df2855f017dcbfc59f4a/vectorize/v2/indexes/openviking-embeddings';

const HTML_CONTENT = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenViking RAG — Ingest & Search</title>
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
      border-radius: 12px; padding: 2.5rem; width: 100%; max-width: 560px;
    }
    .logo { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.15em;
      color: var(--accent); margin-bottom: 0.25rem; }
    h1 { font-size: 1.4rem; font-weight: 600; margin-bottom: 0.25rem; }
    .subtitle { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1.75rem; }
    label { display: block; font-size: 0.8rem; font-weight: 500;
      color: var(--text-muted); margin-bottom: 0.35rem; }
    input, select, textarea {
      width: 100%; padding: 0.6rem 0.75rem; background: var(--bg);
      border: 1px solid var(--border); border-radius: var(--radius);
      color: var(--text); font-size: 0.9rem; outline: none;
      transition: border-color 0.15s; font-family: inherit;
    }
    input:focus, select:focus, textarea:focus { border-color: var(--accent); }
    input::placeholder, textarea::placeholder { color: #475569; }
    textarea { min-height: 120px; resize: vertical; line-height: 1.5; }
    .field { margin-bottom: 1.1rem; }
    select { appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%2394a3b8'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E");
      background-repeat: no-repeat; background-position: right 0.75rem center;
      padding-right: 2rem; cursor: pointer;
    }
    select option { background: var(--surface); color: var(--text); }
    .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.1rem; }
    .tab { flex: 1; padding: 0.5rem; background: var(--bg);
      border: 1px solid var(--border); border-radius: var(--radius);
      color: var(--text-muted); font-size: 0.85rem; font-weight: 500;
      cursor: pointer; transition: all 0.15s; text-align: center;
    }
    .tab.active { background: rgba(56,189,248,0.15);
      border-color: var(--accent); color: var(--accent); }
    .tab:hover:not(.active) { border-color: #334155; color: var(--text); }
    .hidden { display: none !important; }
    .btn {
      width: 100%; padding: 0.7rem; margin-top: 0.5rem;
      background: var(--accent); color: #0b0e14; border: none;
      border-radius: var(--radius); font-size: 0.9rem; font-weight: 600;
      cursor: pointer; transition: background 0.15s;
    }
    .btn:hover:not(:disabled) { background: var(--accent-hover); }
    .btn:disabled { opacity: 0.55; cursor: not-allowed; }
    .btn.secondary { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
    .btn.secondary:hover { background: rgba(56,189,248,0.1); }
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
    .results { margin-top: 1rem; }
    .result-item {
      background: var(--bg); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 0.85rem;
      margin-bottom: 0.5rem; font-size: 0.82rem;
    }
    .result-title { font-weight: 600; color: var(--accent); margin-bottom: 0.25rem; }
    .result-meta { color: #475569; font-size: 0.75rem; margin-bottom: 0.4rem; }
    .result-text { color: var(--text-muted); line-height: 1.4; }
    .score-badge {
      display: inline-block; padding: 0.15rem 0.4rem;
      background: rgba(56,189,248,0.15); color: var(--accent);
      border-radius: 4px; font-size: 0.7rem; font-weight: 600;
      margin-left: 0.5rem;
    }
    .footer { margin-top: 1.5rem; text-align: center; font-size: 0.72rem; color: #475569; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">OpenViking RAG</div>
    <h1>Knowledge Ingest & Search</h1>
    <p class="subtitle">Store documentation and search it semantically across the OpenViking knowledge base.</p>

    <div class="tabs">
      <div class="tab active" data-tab="ingest">Ingest</div>
      <div class="tab" data-tab="search">Search</div>
    </div>

    <div id="ingest_panel">
      <div class="tabs" style="margin-bottom:0.8rem;">
        <button type="button" class="tab active" data-mode="url" id="mode_url">URL</button>
        <button type="button" class="tab" data-mode="text" id="mode_text">Text</button>
      </div>
      <form id="ingest_form" autocomplete="off">
        <div class="field" id="url_field">
          <label for="target_url">Target URL</label>
          <input type="url" id="target_url" name="target_url" placeholder="https://example.com/docs" required>
        </div>
        <div class="field hidden" id="text_field">
          <label for="text_content">Document Text</label>
          <textarea id="text_content" name="text_content" placeholder="Paste or type documentation text..."></textarea>
        </div>
        <div class="field">
          <label for="context_label">Category</label>
          <select id="context_label" name="context_label" required>
            <option value="Component_Documentation" selected>Component Documentation</option>
            <option value="OpenCode_Transcripts">OpenCode Transcripts</option>
            <option value="Planned_Concepts">Planned Concepts</option>
          </select>
        </div>
        <button type="submit" class="btn" id="ingest_btn">
          <span id="ingest_label">Store in OpenViking</span>
          <span class="spinner" id="ingest_spinner"></span>
        </button>
      </form>
    </div>

    <div id="search_panel" class="hidden">
      <form id="search_form" autocomplete="off">
        <div class="field">
          <label for="search_query">Search Query</label>
          <input type="text" id="search_query" name="search_query" placeholder="What are you looking for?" required>
        </div>
        <div class="field">
          <label for="search_category">Filter by Category</label>
          <select id="search_category" name="search_category">
            <option value="">All Categories</option>
            <option value="Component_Documentation">Component Documentation</option>
            <option value="OpenCode_Transcripts">OpenCode Transcripts</option>
            <option value="Planned_Concepts">Planned Concepts</option>
          </select>
        </div>
        <button type="submit" class="btn secondary" id="search_btn">
          <span id="search_label">Search Knowledge Base</span>
          <span class="spinner" id="search_spinner"></span>
        </button>
      </form>
      <div class="results" id="results_box"></div>
    </div>

    <div class="status" id="status_box"></div>
    <div class="footer">OpenViking RAG System · AI Staffing Solutions</div>
  </div>

  <script>
    (function () {
      const tabs = document.querySelectorAll('.tab[data-tab]');
      const ingestPanel = document.getElementById('ingest_panel');
      const searchPanel = document.getElementById('search_panel');
      const modeUrl = document.getElementById('mode_url');
      const modeText = document.getElementById('mode_text');
      const urlField = document.getElementById('url_field');
      const textField = document.getElementById('text_field');
      const urlInput = document.getElementById('target_url');
      const textInput = document.getElementById('text_content');
      let ingestMode = 'url';

      tabs.forEach(t => t.addEventListener('click', () => {
        tabs.forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        if (t.dataset.tab === 'ingest') {
          ingestPanel.classList.remove('hidden');
          searchPanel.classList.add('hidden');
        } else {
          ingestPanel.classList.add('hidden');
          searchPanel.classList.remove('hidden');
        }
      }));

      function setIngestMode(mode) {
        ingestMode = mode;
        if (mode === 'url') {
          modeUrl.classList.add('active'); modeText.classList.remove('active');
          urlField.classList.remove('hidden'); textField.classList.add('hidden');
          urlInput.setAttribute('required', ''); textInput.removeAttribute('required');
        } else {
          modeText.classList.add('active'); modeUrl.classList.remove('active');
          urlField.classList.add('hidden'); textField.classList.remove('hidden');
          urlInput.removeAttribute('required'); textInput.setAttribute('required', '');
        }
      }
      modeUrl.addEventListener('click', () => setIngestMode('url'));
      modeText.addEventListener('click', () => setIngestMode('text'));

      function setLoading(btn, label, spinner, on) {
        btn.disabled = on;
        label.style.display = on ? 'none' : '';
        spinner.style.display = on ? 'block' : 'none';
      }
      function showStatus(type, msg) {
        const s = document.getElementById('status_box');
        s.className = 'status ' + type; s.textContent = msg;
      }
      function clearStatus() {
        document.getElementById('status_box').className = 'status';
        document.getElementById('status_box').textContent = '';
      }

      document.getElementById('ingest_form').addEventListener('submit', async function (e) {
        e.preventDefault(); clearStatus();
        const btn = document.getElementById('ingest_btn');
        const label = document.getElementById('ingest_label');
        const spinner = document.getElementById('ingest_spinner');
        const category = document.getElementById('context_label').value;
        let payload = { context_label: category };
        if (ingestMode === 'url') {
          payload.target_url = urlInput.value.trim();
          if (!payload.target_url) return;
        } else {
          payload.text_content = textInput.value.trim();
          if (!payload.text_content) return;
        }
        setLoading(btn, label, spinner, true);
        try {
          const res = await fetch('/api/store', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (res.ok && data.success) {
            showStatus('ok', '\u2714 ' + data.message);
            if (ingestMode === 'url') urlInput.value = '';
            else textInput.value = '';
          } else {
            showStatus('err', '\u2718 ' + (data.error || 'Failed'));
          }
        } catch (err) {
          showStatus('err', '\u2718 Network error: ' + err.message);
        } finally { setLoading(btn, label, spinner, false); }
      });

      document.getElementById('search_form').addEventListener('submit', async function (e) {
        e.preventDefault(); clearStatus();
        const btn = document.getElementById('search_btn');
        const label = document.getElementById('search_label');
        const spinner = document.getElementById('search_spinner');
        const query = document.getElementById('search_query').value.trim();
        const category = document.getElementById('search_category').value;
        if (!query) return;
        setLoading(btn, label, spinner, true);
        document.getElementById('results_box').innerHTML = '';
        try {
          const res = await fetch('/api/search', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, category: category || undefined })
          });
          const data = await res.json();
          if (res.ok && data.success) {
            const box = document.getElementById('results_box');
            if (!data.results || data.results.length === 0) {
              box.innerHTML = '<div style="color:#475569;font-size:0.85rem;margin-top:0.5rem;">No matching documents found.</div>';
            } else {
              box.innerHTML = data.results.map(r => \`
                <div class="result-item">
                  <div class="result-title">\${r.title || 'Untitled'}<span class="score-badge">\${Math.round((r.score || 0)*100)}%</span></div>
                  <div class="result-meta">\${r.category || 'General'} · \${r.url || 'Text document'} · \${r.timestamp ? new Date(r.timestamp).toLocaleDateString() : ''}</div>
                  <div class="result-text">\${(r.text || '').substring(0, 300)}\${(r.text || '').length > 300 ? '...' : ''}</div>
                </div>
              \`).join('');
            }
          } else {
            showStatus('err', '\u2718 ' + (data.error || 'Search failed'));
          }
        } catch (err) {
          showStatus('err', '\u2718 Network error: ' + err.message);
        } finally { setLoading(btn, label, spinner, false); }
      });
    })();
  </script>
</body>
</html>`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    if (url.pathname === '/' && request.method === 'GET') {
      return htmlResponse(HTML_CONTENT);
    }

    if (url.pathname === '/api/store' && request.method === 'POST') {
      return handleStore(request, env);
    }
    if (url.pathname === '/api/search' && request.method === 'POST') {
      return handleSearch(request, env);
    }
    if (url.pathname === '/api/health' && request.method === 'GET') {
      return jsonResponse({ status: 'ok', service: 'openviking-rag' });
    }

    return jsonResponse({ error: 'Not Found' }, 404);
  },
};

async function handleStore(request, env) {
  let payload;
  try { payload = await request.json(); } catch {
    return jsonResponse({ success: false, error: 'Invalid JSON body.' }, 400);
  }

  const { target_url, text_content, context_label } = payload || {};

  if (!context_label || typeof context_label !== 'string') {
    return jsonResponse({ success: false, error: 'Missing or invalid context_label.' }, 400);
  }

  let content, title, sourceType, scrapedUrl;

  if (target_url && typeof target_url === 'string') {
    scrapedUrl = target_url;
    try {
      const scrapeResult = await scrapeUrl(target_url);
      content = scrapeResult.text;
      title = scrapeResult.title || target_url;
      sourceType = 'url';
    } catch (err) {
      return jsonResponse({ success: false, error: 'Failed to scrape URL: ' + err.message }, 502);
    }
  } else if (text_content && typeof text_content === 'string') {
    content = convertToMarkdown(text_content, context_label);
    title = context_label.replace(/_/g, ' ');
    sourceType = 'text';
  } else {
    return jsonResponse({ success: false, error: 'Provide either target_url or text_content.' }, 400);
  }

  let embedding;
  try {
    embedding = await generateEmbedding(env, content);
  } catch (err) {
    return jsonResponse({ success: false, error: 'Embedding generation failed: ' + err.message }, 500);
  }

  const docId = crypto.randomUUID();
  const timestamp = new Date().toISOString();

  try {
    const insertRes = await fetch(`${VECTORIZE_API}/upsert`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.CF_API_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vectors: [{
          id: docId,
          values: embedding,
          metadata: {
            title: title,
            category: context_label,
            content: content,
            url: scrapedUrl || null,
            source_type: sourceType,
            timestamp: timestamp,
          },
        }],
      }),
    });
    if (!insertRes.ok) {
      const errText = await insertRes.text();
      throw new Error(`Vectorize insert HTTP ${insertRes.status}: ${errText}`);
    }
  } catch (err) {
    return jsonResponse({ success: false, error: 'Vector storage failed: ' + err.message }, 500);
  }

  return jsonResponse({
    success: true,
    message: `${sourceType === 'url' ? 'URL' : 'Text document'} stored and indexed. ID: ${docId}`,
    document_id: docId,
    category: context_label,
    source_type: sourceType,
  });
}

async function handleSearch(request, env) {
  let payload;
  try { payload = await request.json(); } catch {
    return jsonResponse({ success: false, error: 'Invalid JSON body.' }, 400);
  }

  const { query, category, top_k } = payload || {};

  if (!query || typeof query !== 'string') {
    return jsonResponse({ success: false, error: 'Missing or invalid query.' }, 400);
  }

  let embedding;
  try {
    embedding = await generateEmbedding(env, query);
  } catch (err) {
    return jsonResponse({ success: false, error: 'Query embedding failed: ' + err.message }, 500);
  }

  let results;
  try {
    const queryRes = await fetch(`${VECTORIZE_API}/query`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${env.CF_API_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        vector: embedding,
        topK: Math.min(Math.max(parseInt(top_k) || 5, 1), 20),
        returnMetadata: "all",
      }),
    });
    if (!queryRes.ok) {
      const errText = await queryRes.text();
      throw new Error(`Vectorize query HTTP ${queryRes.status}: ${errText}`);
    }
    const queryData = await queryRes.json();
    results = queryData.result?.matches || queryData.matches || [];
  } catch (err) {
    return jsonResponse({ success: false, error: 'Vector search failed: ' + err.message }, 500);
  }

  if (category && typeof category === 'string') {
    results = results.filter(r => r.metadata?.category === category);
  }

  const formatted = results.map(r => ({
    id: r.id,
    score: r.score,
    title: r.metadata?.title || 'Untitled',
    category: r.metadata?.category || 'General',
    text: r.metadata?.content || '',
    url: r.metadata?.url || null,
    timestamp: r.metadata?.timestamp || null,
    source_type: r.metadata?.source_type || 'unknown',
  }));

  return jsonResponse({
    success: true,
    query: query,
    results: formatted,
    total: formatted.length,
  });
}

async function scrapeUrl(url) {
  const response = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; OpenVikingBot/1.0)',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
    redirect: 'follow',
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} from ${url}`);
  }

  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('text/plain') || contentType.includes('text/markdown')) {
    const text = await response.text();
    return { title: url, text: text };
  }

  const html = await response.text();
  return extractTextFromHtml(html, url);
}

function extractTextFromHtml(html, url) {
  let cleaned = html
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<nav[^>]*>[\s\S]*?<\/nav>/gi, ' ')
    .replace(/<header[^>]*>[\s\S]*?<\/header>/gi, ' ')
    .replace(/<footer[^>]*>[\s\S]*?<\/footer>/gi, ' ')
    .replace(/<aside[^>]*>[\s\S]*?<\/aside>/gi, ' ');

  const titleMatch = cleaned.match(/<title[^>]*>([^<]*)<\/title>/i);
  const title = titleMatch ? titleMatch[1].trim() : url;

  const mainMatch = cleaned.match(/<main[^>]*>([\s\S]*?)<\/main>/i);
  const articleMatch = cleaned.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
  const bodyMatch = cleaned.match(/<body[^>]*>([\s\S]*?)<\/body>/i);

  const contentHtml = mainMatch?.[1] || articleMatch?.[1] || bodyMatch?.[1] || cleaned;

  const text = contentHtml
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .trim();

  return { title, text };
}

async function generateEmbedding(env, text) {
  const truncated = text.slice(0, 5000);

  const response = await env.AI.run(EMBED_MODEL, {
    text: [truncated],
  });

  if (!response.data || !response.data[0]) {
    throw new Error('Invalid embedding response from Workers AI');
  }

  // Force conversion to plain JS array for Vectorize compatibility
  return Array.from(response.data[0]);
}

function convertToMarkdown(text, category) {
  const timestamp = new Date().toISOString();
  const title = category.replace(/_/g, ' ');
  const escapedText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return `---\ntitle: "${title}"\ncategory: ${category}\ningested_at: ${timestamp}\nsource: openviking-rag\nformat: markdown\n---\n\n# ${title}\n\n${escapedText}\n`;
}

function htmlResponse(html) {
  return new Response(html, {
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  });
}

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
  });
}

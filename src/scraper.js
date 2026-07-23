/**
 * Cloudflare Edge Intelligence Grid — Browser Rendering Scraper
 *
 * This module is invoked by router.js via the `/scrape` endpoint.
 * It uses the Cloudflare Browser Rendering binding (`EDGE_BROWSER`)
 * to programmatically navigate to target URLs, extract observability
 * data, and return structured results.
 *
 * Capabilities:
 *   - Health-check probing of Cloud Run services (Track A, Track B)
 *   - Metrics endpoint scraping
 *   - Log sampling
 *   - JSON response parsing and normalization
 *   - Timeout-safe navigation with fallback
 *
 * Conforms to the C-P-A model: Context gathering via automated probing.
 * Results are fed back into the router for ingestion and classification.
 */

// ---------------------------------------------------------------------------
// Browser Rendering Scraper — Core Functions
// ---------------------------------------------------------------------------

/**
 * Launch a headless browser session via the EDGE_BROWSER binding and
 * navigate to the target URL. Returns structured observability data.
 *
 * @param {object} browserBinding - Cloudflare Browser Rendering binding (env.EDGE_BROWSER)
 * @param {object} target - { url: string, selector?: string, waitFor?: string, timeout?: number }
 * @returns {object} Structured scrape result with metrics, status, and timing
 */
export async function scrape(browserBinding, target) {
  if (!browserBinding) {
    return {
      status: 'unavailable',
      error: 'EDGE_BROWSER binding not configured',
    };
  }

  const url = target.url;
  const timeout = target.timeout || 15000;
  const selector = target.selector || null;
  const waitFor = target.waitFor || 'networkidle0';

  if (!url) {
    return { status: 'error', error: 'No target URL provided' };
  }

  const startTime = Date.now();
  let browser = null;

  try {
    // Launch browser with resource constraints
    browser = await browserBinding.launch({
      headless: true,
    });

    const page = await browser.newPage();

    // Set a reasonable viewport
    await page.setViewport({ width: 1280, height: 720 });

    // Block unnecessary resources for speed (images, fonts, media)
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const resourceType = req.resourceType();
      if (['image', 'font', 'media', 'stylesheet'].includes(resourceType)) {
        req.abort();
      } else {
        req.continue();
      }
    });

    // Navigate to target
    const navigationStart = Date.now();
    const response = await page.goto(url, {
      waitUntil: waitFor,
      timeout: timeout,
    });

    const navigationLatency = Date.now() - navigationStart;
    const httpStatus = response ? response.status() : 0;

    // Extract content based on strategy
    let content = null;
    let extractionMethod = 'none';

    if (selector) {
      // Targeted element extraction
      try {
        content = await page.$eval(selector, (el) => el.textContent);
        extractionMethod = 'selector';
      } catch {
        extractionMethod = 'selector_failed';
      }
    }

    if (!content) {
      // Fall back to full page content
      content = await page.content();
      extractionMethod = extractionMethod === 'none' ? 'full_page' : extractionMethod + '+full_page';
    }

    // Attempt JSON parsing if content looks like JSON
    let parsedBody = null;
    try {
      // Try parsing text content as JSON
      const textContent = await page.evaluate(() => document.body.innerText);
      parsedBody = JSON.parse(textContent);
    } catch {
      // Not JSON — keep as raw text
      parsedBody = null;
    }

    // Capture page title
    const pageTitle = await page.title();

    // Evaluate custom metrics from the page context
    const customMetrics = await page.evaluate(() => {
      const metrics = {};

      // DOM node count
      metrics.dom_node_count = document.getElementsByTagName('*').length;

      // Script count
      metrics.script_count = document.getElementsByTagName('script').length;

      // Body size
      const body = document.body;
      metrics.body_text_length = body ? body.innerText.length : 0;

      // Any console errors (if captured in page context)
      metrics.has_qsa_errors =
        typeof window.__qsa_errors !== 'undefined' && window.__qsa_errors > 0;

      return metrics;
    });

    await browser.close();
    browser = null;

    const totalLatency = Date.now() - startTime;

    return {
      status: 'success',
      target: url,
      http_status: httpStatus,
      navigation_latency_ms: navigationLatency,
      total_latency_ms: totalLatency,
      page_title: pageTitle,
      extraction_method: extractionMethod,
      content_type: parsedBody ? 'json' : 'text',
      data: parsedBody || content,
      metrics: {
        ...customMetrics,
        content_length: content ? content.length : 0,
      },
      timestamp: new Date().toISOString(),
    };
  } catch (err) {
    if (browser) {
      try {
        await browser.close();
      } catch {
        // browser may already be closed
      }
    }

    return {
      status: 'error',
      target: url,
      error: err.message,
      error_type: err.name || 'Error',
      latency_ms: Date.now() - startTime,
      timestamp: new Date().toISOString(),
    };
  }
}

/**
 * Probe multiple endpoints and return a health matrix.
 * Used for systematic health checking of the C-P-A pipeline.
 *
 * @param {object} browserBinding - Cloudflare Browser Rendering binding
 * @param {string[]} endpoints - Array of URLs to probe
 * @returns {object} Health matrix with per-endpoint results
 */
export async function probeHealth(browserBinding, endpoints) {
  if (!endpoints || endpoints.length === 0) {
    return { status: 'error', error: 'No endpoints provided' };
  }

  const results = {};
  const startTime = Date.now();

  // Probe endpoints sequentially to avoid overwhelming the browser rendering
  for (const endpoint of endpoints) {
    const result = await scrape(browserBinding, {
      url: endpoint,
      timeout: 10000,
      waitFor: 'domcontentloaded',
    });

    // Use the URL as key, sanitized
    const key = endpoint.replace(/[^a-zA-Z0-9]/g, '_');
    results[key] = {
      url: endpoint,
      healthy: result.status === 'success' && result.http_status >= 200 && result.http_status < 400,
      http_status: result.http_status,
      latency_ms: result.total_latency_ms || result.latency_ms,
      error: result.error || null,
    };
  }

  return {
    status: 'complete',
    endpoints_probed: endpoints.length,
    healthy_count: Object.values(results).filter((r) => r.healthy).length,
    total_latency_ms: Date.now() - startTime,
    results,
    timestamp: new Date().toISOString(),
  };
}

// ---------------------------------------------------------------------------
// Default export: invoked by router.js via EDGE_BROWSER binding
// when Cloudflare Workers use module-based custom services
// ---------------------------------------------------------------------------
export default {
  scrape,
  probeHealth,
};

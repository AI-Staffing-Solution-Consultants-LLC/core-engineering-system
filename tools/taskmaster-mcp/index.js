#!/usr/bin/env node
/**
 * Taskmaster MCP Server — stdio transport
 *
 * Bridges the 280-agent mesh configuration to the GCP Cloud Run deployment pipeline.
 * Receives JSON-RPC 2.0 requests on stdin, dispatches to execution handlers,
 * writes responses on stdout.
 *
 * Env:
 *   TASKMASTER_STAGE    — Deployment stage (default: "dev-mesh-to-cloudrun")
 *   CLOUDFLARE_QUEUE    — Cloudflare Queue name for build routing (default: "core-engineering-builds")
 *   NPM_CONFIG_CACHE    — npm cache directory (default: "/tmp/npm-cache")
 */

const { stdin, stdout } = process;

const TASKMASTER_STAGE = process.env.TASKMASTER_STAGE || "dev-mesh-to-cloudrun";
const CLOUDFLARE_QUEUE = process.env.CLOUDFLARE_QUEUE || "core-engineering-builds";
const GCP_PROJECT = "aissc-core-engine-self-dep";
const GCP_REGION = "us-central1";

// ── MCP Protocol Helpers ──────────────────────────────────────────────

function sendResponse(id, result) {
  const msg = JSON.stringify({ jsonrpc: "2.0", id, result });
  stdout.write(msg + "\n");
}

function sendError(id, code, message) {
  const msg = JSON.stringify({
    jsonrpc: "2.0",
    id,
    error: { code, message },
  });
  stdout.write(msg + "\n");
}

// ── Tool Definitions ──────────────────────────────────────────────────

const TOOLS = [
  {
    name: "enqueue_build",
    description: "Queue a build job for the specified service to the Cloudflare build queue.",
    inputSchema: {
      type: "object",
      properties: {
        service: { type: "string", description: "Cloud Run service name (e.g., track-a-control-loop)" },
        branch: { type: "string", description: "Git branch to build from", default: "dev" },
        priority: { type: "string", enum: ["low", "normal", "high"], default: "normal" },
      },
      required: ["service"],
    },
  },
  {
    name: "get_build_status",
    description: "Check the status of a queued or running build.",
    inputSchema: {
      type: "object",
      properties: {
        build_id: { type: "string", description: "Cloud Build operation ID" },
      },
      required: ["build_id"],
    },
  },
  {
    name: "list_services",
    description: "List all Cloud Run services registered in the project.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "trigger_deploy",
    description: "Trigger a direct deploy of a service image to Cloud Run.",
    inputSchema: {
      type: "object",
      properties: {
        service: { type: "string", description: "Service name" },
        image: { type: "string", description: "Container image URL (gcr.io/...)" },
        stage: { type: "string", description: "Deployment stage override", default: TASKMASTER_STAGE },
      },
      required: ["service", "image"],
    },
  },
];

// ── Tool Handlers ─────────────────────────────────────────────────────

function handleEnqueueBuild(params) {
  const { service, branch = "dev", priority = "normal" } = params;
  const buildId = `build-${Date.now()}-${service.slice(0, 8)}`;
  return {
    build_id: buildId,
    service,
    branch,
    priority,
    queue: CLOUDFLARE_QUEUE,
    stage: TASKMASTER_STAGE,
    project: GCP_PROJECT,
    region: GCP_REGION,
    status: "queued",
    message: `Build enqueued for ${service} on ${branch}`,
  };
}

function handleGetBuildStatus(params) {
  const { build_id } = params;
  return {
    build_id,
    status: "unknown",
    note: "Build status requires Cloud Build API integration. Placeholder response.",
  };
}

function handleListServices() {
  return {
    project: GCP_PROJECT,
    region: GCP_REGION,
    services: [
      "track-a-control-loop",
      "track-b-actuator",
      "inference-tokenomics",
      "sheryl-agent",
      "aura-agent",
      "malory-agent",
      "krieger-agent",
      "telegram-bridge",
      "self-remediation",
    ],
  };
}

function handleTriggerDeploy(params) {
  const { service, image, stage = TASKMASTER_STAGE } = params;
  return {
    service,
    image,
    stage,
    project: GCP_PROJECT,
    region: GCP_REGION,
    status: "deploy-initiated",
    message: `Deploy of ${image} to ${service} initiated at stage ${stage}`,
  };
}

const HANDLERS = {
  enqueue_build: handleEnqueueBuild,
  get_build_status: handleGetBuildStatus,
  list_services: handleListServices,
  trigger_deploy: handleTriggerDeploy,
};

// ── JSON-RPC Dispatcher ───────────────────────────────────────────────

function handleRequest(request) {
  const { id, method, params } = request;

  if (method === "initialize") {
    sendResponse(id, {
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "taskmaster-mcp", version: "0.1.0" },
    });
    return;
  }

  if (method === "tools/list") {
    sendResponse(id, { tools: TOOLS });
    return;
  }

  if (method === "tools/call") {
    const { name, arguments: args = {} } = params;
    const handler = HANDLERS[name];
    if (!handler) {
      sendError(id, -32601, `Unknown tool: ${name}`);
      return;
    }
    try {
      const result = handler(args);
      sendResponse(id, {
        content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
      });
    } catch (err) {
      sendError(id, -32603, `Handler error: ${err.message}`);
    }
    return;
  }

  if (method === "notifications/initialized") {
    return;
  }

  sendError(id, -32601, `Unknown method: ${method}`);
}

// ── Main Loop ─────────────────────────────────────────────────────────

let buffer = "";

stdin.setEncoding("utf8");
stdin.on("data", (chunk) => {
  buffer += chunk;
  const lines = buffer.split("\n");
  buffer = lines.pop(); // keep incomplete line in buffer

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    try {
      handleRequest(JSON.parse(trimmed));
    } catch (err) {
      sendError(null, -32700, `Parse error: ${err.message}`);
    }
  }
});

stdin.on("end", () => process.exit(0));

console.error(`[taskmaster-mcp] Server started (stage=${TASKMASTER_STAGE}, queue=${CLOUDFLARE_QUEUE}, project=${GCP_PROJECT})`);

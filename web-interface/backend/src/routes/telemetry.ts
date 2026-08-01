import { Router, type Request, type Response } from "express"

const telemetryRouter = Router()

// ---------------------------------------------------------------------------
// Service keys — matches all 9 grid slots in CommandDashboard SERVICES list
// ---------------------------------------------------------------------------
type ServiceKey =
  | "sheryl"
  | "aura"
  | "malory"
  | "krieger"
  | "selfRemediation"
  | "telegram"
  | "trackA"
  | "trackB"
  | "agencyAgents"

type ServiceStatus = Record<ServiceKey, "ok" | "unreachable">

// ---------------------------------------------------------------------------
// Probe helper
// ---------------------------------------------------------------------------
const PROBE_TIMEOUT_MS = 5000

async function probe(url: string | undefined, path = "/healthz"): Promise<"ok" | "unreachable"> {
  if (!url) return "unreachable"
  try {
    const ctrl = new AbortController()
    const id = setTimeout(() => ctrl.abort(), PROBE_TIMEOUT_MS)
    const res = await fetch(`${url}${path}`, {
      method: "GET",
      signal: ctrl.signal,
      headers: { "User-Agent": "web-interface-telemetry/1.0" },
    })
    clearTimeout(id)
    return res.ok ? "ok" : "unreachable"
  } catch {
    return "unreachable"
  }
}

// ---------------------------------------------------------------------------
// Probe all 9 services in parallel
// ---------------------------------------------------------------------------
async function probeAll(): Promise<ServiceStatus> {
  const [sheryl, aura, malory, krieger, selfRemediation, telegram, trackA, trackB] =
    await Promise.all([
      probe(process.env["SHERYL_URL"]),
      probe(process.env["AURA_URL"]),
      probe(process.env["MALORY_URL"]),
      probe(process.env["KRIEGER_URL"]),
      probe(process.env["SELF_REMEDIATION_URL"]),
      probe(process.env["TELEGRAM_BRIDGE_URL"]),
      probe(process.env["TRACK_A_URL"]),
      probe(process.env["TRACK_B_URL"]),
    ])

  // agency-agents-daemon is commented out in docker-compose.yml — no env var,
  // so probe is truthfully unreachable
  const agencyAgents: "ok" | "unreachable" = "unreachable"

  return { sheryl, aura, malory, krieger, selfRemediation, telegram, trackA, trackB, agencyAgents }
}

// ---------------------------------------------------------------------------
// Fetch Track A ledger entries
// ---------------------------------------------------------------------------
interface LedgerEntry {
  id?: string
  timestamp?: string
  payload?: unknown
  chain_hash?: string
  type?: string
}

interface LedgerBatchEvent {
  type: "ledger"
  timestamp: string
  entries: LedgerEntry[]
}

async function fetchLedger(): Promise<LedgerBatchEvent | null> {
  const url = process.env["TRACK_A_URL"]
  if (!url) return null

  try {
    const ctrl = new AbortController()
    const id = setTimeout(() => ctrl.abort(), 5000)
    const res = await fetch(`${url}/ledger?limit=20`, { method: "GET", signal: ctrl.signal })
    clearTimeout(id)

    if (!res.ok) return null

    const data = (await res.json()) as { entries?: unknown[] }
    if (!Array.isArray(data.entries) || data.entries.length === 0) return null

    return {
      type: "ledger",
      timestamp: new Date().toISOString(),
      entries: data.entries as LedgerEntry[],
    }
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// SSE helper
// ---------------------------------------------------------------------------
function sendSSE(res: Response, data: unknown): void {
  res.write(`data: ${JSON.stringify(data)}\n\n`)
}

// ---------------------------------------------------------------------------
// SSE stream: GET /api/telemetry
// Pushes real telemetry every 10s + Track A ledger entries
// ---------------------------------------------------------------------------
telemetryRouter.get("/", (_req: Request, res: Response): void => {
  res.setHeader("Content-Type", "text/event-stream")
  res.setHeader("Cache-Control", "no-cache")
  res.setHeader("Connection", "keep-alive")
  res.setHeader("X-Accel-Buffering", "no")
  res.flushHeaders()

  let running = true

  async function push(): Promise<void> {
    if (!running) return
    try {
      const services = await probeAll()
      const allOk: boolean = Object.values(services).every((s) => s === "ok")

      sendSSE(res, {
        type: "telemetry",
        healthy: allOk,
        services,
        timestamp: new Date().toISOString(),
      })

      const batch = await fetchLedger()
      if (batch) {
        sendSSE(res, batch)
      }
    } catch {
      // push failure — skip silently, retry next interval
    }
  }

  // Initial push immediately
  void push()

  const intervalId = setInterval(() => {
    void push()
  }, 10000)

  res.on("close", () => {
    running = false
    clearInterval(intervalId)
    res.end()
  })
})

// ---------------------------------------------------------------------------
// Polling fallback: GET /api/telemetry/poll
// Returns same 9-service shape as a JSON snapshot
// ---------------------------------------------------------------------------
telemetryRouter.get("/poll", async (_req: Request, res: Response): Promise<void> => {
  const services = await probeAll()
  const allOk: boolean = Object.values(services).every((s) => s === "ok")

  res.json({
    healthy: allOk,
    services,
    timestamp: new Date().toISOString(),
  })
})

export { telemetryRouter }

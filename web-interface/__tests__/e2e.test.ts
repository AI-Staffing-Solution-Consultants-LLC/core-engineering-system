import { execSync, type ExecSyncOptions } from "node:child_process"
import { describe, test, expect, beforeAll, afterAll } from "vitest"

const COMPOSE_DIR = "/home/olly/core-engineering-system"
const BASE_URL = "http://localhost:3001"
const API_TOKEN = "dev-token"

const SERVICES = [
  { name: "track-a-control-loop", port: 8080 },
  { name: "track-b-actuator", port: 8081 },
  { name: "sheryl", port: 8083 },
  { name: "aura-agent", port: 8084 },
  { name: "malory", port: 8085 },
  { name: "krieger", port: 8086 },
  { name: "self-remediation", port: 8087 },
  { name: "telegram-bridge", port: 8088 },
  { name: "web-interface-backend", port: 3001 },
]

function run(cmd: string, opts?: ExecSyncOptions): string {
  return execSync(cmd, {
    encoding: "utf-8",
    cwd: COMPOSE_DIR,
    stdio: "pipe",
    timeout: 600_000,
    ...opts,
  })
}

async function fetchWithToken(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...init?.headers,
      "Authorization": `Bearer ${API_TOKEN}`,
    },
  })
}

async function pollHealth(port: number, maxWaitMs: number): Promise<boolean> {
  const start = Date.now()
  while (Date.now() - start < maxWaitMs) {
    try {
      const res = await fetch(`http://localhost:${port}/healthz`, {
        method: "GET",
        signal: AbortSignal.timeout(3000),
      })
      if (res.ok) return true
    } catch {
      // not ready yet
    }
    await new Promise((r) => setTimeout(r, 2000))
  }
  return false
}

describe("E2E Integration — full pipeline frontend→backend→Sheryl", { timeout: 900_000 }, () => {
  beforeAll(async () => {
    console.log("=== Pre-clean: stopping any stale containers ===")
    run("docker compose down --remove-orphans 2>/dev/null || true")

    // Pre-stage shared files needed by Dockerfiles whose build context
    // differs from where the source files live. Pattern from deploy-gcr.sh:
    //   sheryl + aura: build context is repo root, need memory_client.py there
    //   malory + krieger: build context is their own dir, need memory_client.py there
    //   self-remediation: build context is ./self-remediation, needs src/ there
    console.log("=== Staging shared dependencies for Docker build ===")
    run("cp ./executive-quartet/memory_client.py ./")
    run("cp ./executive-quartet/memory_client.py ./executive-quartet/malory/")
    run("cp ./executive-quartet/memory_client.py ./executive-quartet/krieger/")
    run("cp -r ./src ./self-remediation/src")

    console.log("=== Building and starting all services ===")
    run("docker compose up -d", { timeout: 600_000 })

    console.log("=== Waiting for all service health checks ===")
    const HEALTH_WINDOW_MS = 180_000
    const results = await Promise.all(
      SERVICES.map(async (svc) => {
        const ok = await pollHealth(svc.port, HEALTH_WINDOW_MS)
        return { ...svc, ok }
      }),
    )

    const failed = results.filter((r) => !r.ok)
    if (failed.length > 0) {
      const names = failed.map((r) => `${r.name}:${r.port}`).join(", ")
      console.error(`HEALTHCHECK FAILED for: ${names}`)
      // dump compose ps for debugging
      try {
        console.error(run("docker compose ps"))
      } catch { /* ignore */ }
    }

    // Track B has a healthcheck dependency chain; if it failed, Track A won't be healthy either.
    // sheryl depends on nothing hard (no depends_on in compose), so it can be independently healthy.
    expect(failed, `Services failed healthcheck: ${failed.map((f) => f.name).join(", ")}`).toHaveLength(0)

    // Extra buffer for sheryl warm-up (MemoryPlugin init can lag)
    await new Promise((r) => setTimeout(r, 3000))

    console.log("=== All services healthy — starting tests ===")
  }, 900_000)

  afterAll(async () => {
    console.log("=== Tearing down all containers ===")
    try {
      run("docker compose down", { timeout: 120_000 })
    } catch (e) {
      console.error("docker compose down failed:", String(e))
      try {
        run("docker compose down --remove-orphans -v", { timeout: 120_000 })
      } catch { /* nothing left to do */ }
    }

    // Remove staged shared files to leave no trace
    console.log("=== Cleaning up staged build-context files ===")
    run("rm -f ./memory_client.py")
    run("rm -f ./executive-quartet/malory/memory_client.py")
    run("rm -f ./executive-quartet/krieger/memory_client.py")
    run("rm -rf ./self-remediation/src")
  }, 300_000)

  test("GET /api/health reports services", async () => {
    const res = await fetchWithToken("/api/health")
    expect(res.status).toBe(200)

    const body = (await res.json()) as {
      healthy: boolean
      services: { sheryl: string; trackA: string; trackB: string; telegram: string }
    }

    expect(typeof body.healthy).toBe("boolean")
    expect(body.services).toBeDefined()
    expect(body.services.sheryl).toBe("ok")
    expect(body.services.trackA).toBe("ok")
    expect(body.services.trackB).toBe("ok")
    expect(body.services.telegram).toBe("ok")
  })

  test("POST /api/command returns plan_id from Sheryl", async () => {
    const res = await fetchWithToken("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "status check" }),
    })

    expect(res.status).toBe(200)

    const body = (await res.json()) as Record<string, unknown>
    expect(body).toHaveProperty("plan_id")
    expect(typeof body.plan_id).toBe("string")
    expect((body.plan_id as string).length).toBeGreaterThan(0)
    expect(body).toHaveProperty("query", "status check")
  })

  test("GET /api/telemetry emits SSE event within 15s", async () => {
    const res = await fetchWithToken("/api/telemetry")

    expect(res.status).toBe(200)
    expect(res.headers.get("content-type")).toContain("text/event-stream")

    const reader = res.body?.getReader()
    expect(reader).toBeDefined()

    const decoder = new TextDecoder()
    let buffer = ""
    const deadline = Date.now() + 15_000
    let foundTelemetry = false
    let lastEvent: unknown = null

    while (reader && Date.now() < deadline) {
      const result = await reader.read()
      if (result.done) break

      buffer += decoder.decode(result.value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const jsonStr = line.slice(6)
        try {
          const event = JSON.parse(jsonStr) as { type?: string }
          lastEvent = event
          if (event.type === "telemetry") {
            foundTelemetry = true
            break
          }
        } catch {
          // malformed event — skip
        }
      }
      if (foundTelemetry) break
    }

    if (reader) {
      await reader.cancel()
      reader.releaseLock()
    }

    expect(foundTelemetry, `SSE telemetry event not received within 15s. Last event: ${JSON.stringify(lastEvent)}`).toBe(true)

    // Verify the telemetry event shape
    const telemetryEvent = lastEvent as { type: string; healthy: boolean; services: Record<string, string>; timestamp: string }
    expect(telemetryEvent.type).toBe("telemetry")
    expect(typeof telemetryEvent.healthy).toBe("boolean")
    expect(typeof telemetryEvent.timestamp).toBe("string")
    expect(telemetryEvent.services).toBeDefined()

    // All 9 service keys should be present
    const expectedKeys = ["sheryl", "aura", "malory", "krieger", "selfRemediation", "telegram", "trackA", "trackB", "agencyAgents"]
    for (const key of expectedKeys) {
      expect(telemetryEvent.services).toHaveProperty(key)
    }
    // At minimum, sheryl should be "ok" (always first non-dependent service)
    expect(telemetryEvent.services.sheryl).toBe("ok")
  })

  test("GET /api/command without token returns 401", async () => {
    const res = await fetch(`${BASE_URL}/api/command`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "status check" }),
    })
    expect(res.status).toBe(401)
  })
})

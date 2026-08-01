import http from "node:http"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"
import express from "express"

import { healthRouter } from "../routes/health.js"

// ---------- helpers ----------

function makeJsonRequest(
  port: number,
  path: string,
): Promise<{ status: number; body: unknown }> {
  return new Promise((resolve, reject) => {
    http
      .get(`http://127.0.0.1:${port}${path}`, { headers: { accept: "application/json" } }, (res) => {
        let raw = ""
        res.on("data", (chunk: Buffer) => {
          raw += chunk.toString()
        })
        res.on("end", () => {
          let body: unknown
          try {
            body = JSON.parse(raw)
          } catch {
            body = raw
          }
          resolve({ status: res.statusCode ?? 500, body })
        })
      })
      .on("error", reject)
  })
}

// ---------- test app ----------

function buildApp(): { app: express.Express; server: ReturnType<express.Express["listen"]>; port: number } {
  const app = express()
  app.use(express.json())
  app.use("/api/health", healthRouter)

  const server = app.listen(0)
  const address = server.address()
  if (!address || typeof address === "string") {
    throw new Error("Failed to get server port")
  }
  const port = address.port
  return { app, server, port }
}

// ---------- tests ----------

describe("GET /api/health", () => {
  let port: number
  let server: ReturnType<express.Express["listen"]>
  let app: express.Express
  const mockFetch = vi.fn<typeof fetch>()

  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch)
    vi.stubEnv("SHERYL_URL", "http://sheryl:8080")
    vi.stubEnv("TRACK_A_URL", "http://track-a:8080")
    vi.stubEnv("TRACK_B_URL", "http://track-b:8081")
    vi.stubEnv("TELEGRAM_BRIDGE_URL", "http://telegram:8080")
    const fixture = buildApp()
    app = fixture.app
    server = fixture.server
    port = fixture.port
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    server.close()
  })

  test("returns 200 with healthy:true when all C-P-A services are up", async () => {
    mockFetch.mockResolvedValue(new Response("ok", { status: 200 }))

    const { status, body } = await makeJsonRequest(port, "/api/health")

    expect(status).toBe(200)
    expect(body).toMatchObject({
      healthy: true,
      services: {
        sheryl: "ok",
        trackA: "ok",
        trackB: "ok",
        telegram: "ok",
      },
    })
  })

  test("returns 200 with healthy:false when one service is down", async () => {
    // Sheryl is down, others are up
    mockFetch
      .mockRejectedValueOnce(new Error("Connection refused")) // sheryl
      .mockResolvedValueOnce(new Response("ok", { status: 200 })) // trackA
      .mockResolvedValueOnce(new Response("ok", { status: 200 })) // trackB
      .mockResolvedValueOnce(new Response("ok", { status: 200 })) // telegram

    const { status, body } = await makeJsonRequest(port, "/api/health")

    expect(status).toBe(200)
    expect(body).toMatchObject({
      healthy: false,
      services: {
        sheryl: "unreachable",
        trackA: "ok",
        trackB: "ok",
        telegram: "ok",
      },
    })
  })

  test("returns 200 with healthy:false when all services are down", async () => {
    mockFetch.mockRejectedValue(new Error("Connection refused"))

    const { status, body } = await makeJsonRequest(port, "/api/health")

    expect(status).toBe(200)

    const data = body as Record<string, unknown>
    expect(data["healthy"]).toBe(false)
    const svc = data["services"] as Record<string, string>
    expect(svc["sheryl"]).toBe("unreachable")
    expect(svc["trackA"]).toBe("unreachable")
    expect(svc["trackB"]).toBe("unreachable")
    expect(svc["telegram"]).toBe("unreachable")
  })

  test("returns 'unreachable' per service when fetch times out", async () => {
    // Simulate timeout: fetch throws an error
    mockFetch.mockRejectedValue(new DOMException("The operation was aborted", "AbortError"))

    const { body } = await makeJsonRequest(port, "/api/health")

    const data = body as Record<string, unknown>
    const svc = data["services"] as Record<string, string>
    expect(svc["sheryl"]).toBe("unreachable")
    expect(svc["trackA"]).toBe("unreachable")
    expect(svc["trackB"]).toBe("unreachable")
    expect(svc["telegram"]).toBe("unreachable")
  })

  test("reports 'unreachable' for services with undefined URLs", async () => {
    // delete env vars so probeService gets undefined URLs
    vi.stubEnv("SHERYL_URL", "")
    vi.stubEnv("TRACK_A_URL", "")
    vi.stubEnv("TRACK_B_URL", "")
    vi.stubEnv("TELEGRAM_BRIDGE_URL", "")

    // fresh app picks up the empty env vars
    server.close()
    const fixture = buildApp()
    port = fixture.port
    server = fixture.server

    const { body } = await makeJsonRequest(port, "/api/health")

    const data = body as Record<string, unknown>
    const svc = data["services"] as Record<string, string>
    expect(svc["sheryl"]).toBe("unreachable")
    expect(svc["trackA"]).toBe("unreachable")
    expect(svc["trackB"]).toBe("unreachable")
    expect(svc["telegram"]).toBe("unreachable")
  })
})

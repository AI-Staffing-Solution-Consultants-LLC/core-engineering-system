import http from "node:http"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"
import express from "express"

import { commandRouter } from "../routes/command.js"

// ---------- helpers ----------

function makeRequest(
  port: number,
  path: string,
  method: "GET" | "POST" = "POST",
  body?: unknown,
): Promise<{ status: number; body: unknown }> {
  return new Promise((resolve, reject) => {
    const json = body !== undefined ? JSON.stringify(body) : undefined
    const headers: http.OutgoingHttpHeaders = {
      "content-type": "application/json",
      accept: "application/json",
    }
    if (json) headers["content-length"] = String(Buffer.byteLength(json))
    const options: http.RequestOptions = {
      hostname: "127.0.0.1",
      port,
      path,
      method,
      headers,
    }

    const req = http.request(options, (res) => {
      let raw = ""
      res.on("data", (chunk: Buffer) => {
        raw += chunk.toString()
      })
      res.on("end", () => {
        let respBody: unknown
        try {
          respBody = JSON.parse(raw)
        } catch {
          respBody = raw
        }
        resolve({ status: res.statusCode ?? 500, body: respBody })
      })
    })
    req.on("error", reject)
    if (json) req.write(json)
    req.end()
  })
}

// ---------- test app ----------

function buildApp(): { app: express.Express; server: ReturnType<express.Express["listen"]>; port: number } {
  const app = express()
  app.use(express.json())
  app.use("/api/command", commandRouter)

  const server = app.listen(0)
  const address = server.address()
  if (!address || typeof address === "string") {
    throw new Error("Failed to get server port")
  }
  const port = address.port
  return { app, server, port }
}

// ---------- tests ----------

describe("POST /api/command", () => {
  let port: number
  let server: ReturnType<express.Express["listen"]>
  const mockFetch = vi.fn<typeof fetch>()

  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch)
    vi.stubEnv("SHERYL_URL", "http://sheryl:8080")
    const fixture = buildApp()
    server = fixture.server
    port = fixture.port
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    server.close()
  })

  test("valid query returns 200 with plan_id in response", async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ plan_id: "plan-abc123", steps: [] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    )

    const { status, body } = await makeRequest(port, "/api/command", "POST", {
      query: "why is latency high",
    })

    expect(status).toBe(200)
    expect(body).toMatchObject({ plan_id: "plan-abc123" })
  })

  test("missing query returns 400", async () => {
    const { status, body } = await makeRequest(port, "/api/command", "POST", {})

    expect(status).toBe(400)
    expect(body).toMatchObject({
      error: expect.stringContaining("Missing or invalid 'query'"),
    })
  })

  test("empty query string returns 400", async () => {
    const { status, body } = await makeRequest(port, "/api/command", "POST", { query: "   " })

    expect(status).toBe(400)
    expect(body).toMatchObject({
      error: expect.stringContaining("Missing or invalid 'query'"),
    })
  })

  test("upstream returns non-ok → 502", async () => {
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ error: "internal" }), { status: 500 }),
    )

    const { status, body } = await makeRequest(port, "/api/command", "POST", {
      query: "why is latency high",
    })

    expect(status).toBe(502)
    expect(body).toMatchObject({
      error: expect.stringContaining("500"),
    })
  })

  test("Sheryl unreachable → 502", async () => {
    mockFetch.mockRejectedValue(new Error("Connection refused"))

    const { status, body } = await makeRequest(port, "/api/command", "POST", {
      query: "why is latency high",
    })

    expect(status).toBe(502)
    expect(body).toMatchObject({
      error: "Failed to reach upstream service",
    })
  })

  test("upstream request times out → 504", async () => {
    mockFetch.mockRejectedValue(new DOMException("The operation was aborted", "AbortError"))

    const { status, body } = await makeRequest(port, "/api/command", "POST", {
      query: "why is latency high",
    })

    expect(status).toBe(504)
    expect(body).toMatchObject({
      error: "Request to upstream service timed out",
    })
  })

  test("SHERYL_URL not set → 500", async () => {
    vi.stubEnv("SHERYL_URL", "")

    const { status, body } = await makeRequest(port, "/api/command", "POST", {
      query: "why is latency high",
    })

    expect(status).toBe(500)
    expect(body).toMatchObject({
      error: expect.stringContaining("SHERYL_URL"),
    })
  })
})

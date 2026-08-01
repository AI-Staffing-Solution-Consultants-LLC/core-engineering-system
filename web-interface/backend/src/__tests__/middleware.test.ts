import http from "node:http"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"
import express, { type Response } from "express"

import { authMiddleware } from "../middleware/auth.js"

// ---------- helpers ----------

function makeRequest(
  port: number,
  path: string,
  method: "GET" | "POST" = "GET",
  headers?: Record<string, string>,
): Promise<{ status: number; body: unknown }> {
  return new Promise((resolve, reject) => {
    const options: http.RequestOptions = {
      hostname: "127.0.0.1",
      port,
      path,
      method,
      headers: {
        accept: "application/json",
        ...headers,
      },
    }

    const req = http.request(options, (res) => {
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
    req.on("error", reject)
    req.end()
  })
}

// ---------- test app ----------

function buildApp(): { app: express.Express; server: ReturnType<express.Express["listen"]>; port: number } {
  const app = express()
  app.use(express.json())
  app.use(authMiddleware)

  app.get("/healthz", (_req, res: Response) => {
    res.json({ status: "ok" })
  })

  app.post("/api/auth", (_req, res: Response) => {
    res.json({ authenticated: true, token: "mock-token" })
  })

  app.get("/api/health", (_req, res: Response) => {
    res.json({ healthy: true })
  })

  const server = app.listen(0)
  const address = server.address()
  if (!address || typeof address === "string") {
    throw new Error("Failed to get server port")
  }
  const port = address.port
  return { app, server, port }
}

// ---------- tests ----------

describe("authMiddleware", () => {
  const VALID_TOKEN = "super-secret-token"

  let port: number
  let server: ReturnType<express.Express["listen"]>

  beforeEach(() => {
    vi.stubEnv("API_TOKEN", VALID_TOKEN)
    const fixture = buildApp()
    server = fixture.server
    port = fixture.port
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    server.close()
  })

  test("no Authorization header with API_TOKEN set → 401", async () => {
    const { status, body } = await makeRequest(port, "/api/health")

    expect(status).toBe(401)
    expect(body).toMatchObject({ error: "Unauthorized" })
  })

  test("valid Bearer token → passes through to route", async () => {
    const { status, body } = await makeRequest(port, "/api/health", "GET", {
      authorization: `Bearer ${VALID_TOKEN}`,
    })

    expect(status).toBe(200)
    expect(body).toMatchObject({ healthy: true })
  })

  test("wrong Bearer token → 401", async () => {
    const { status, body } = await makeRequest(port, "/api/health", "GET", {
      authorization: "Bearer wrong-token",
    })

    expect(status).toBe(401)
    expect(body).toMatchObject({ error: "Unauthorized" })
  })

  test("/healthz bypasses auth middleware without token", async () => {
    const { status, body } = await makeRequest(port, "/healthz")

    expect(status).toBe(200)
    expect(body).toMatchObject({ status: "ok" })
  })

  test("/api/auth bypasses auth middleware without token", async () => {
    const { status, body } = await makeRequest(port, "/api/auth", "POST", {
      "content-type": "application/json",
    })

    expect(status).toBe(200)
    expect(body).toMatchObject({ authenticated: true })
  })

  test("dev mode — no API_TOKEN set → all routes pass without auth", async () => {
    // Clear the token env var
    vi.stubEnv("API_TOKEN", "")

    const { status, body } = await makeRequest(port, "/api/health")

    expect(status).toBe(200)
    expect(body).toMatchObject({ healthy: true })
  })

  test("authorization header without Bearer prefix → 401", async () => {
    const { status, body } = await makeRequest(port, "/api/health", "GET", {
      authorization: VALID_TOKEN,
    })

    expect(status).toBe(401)
    expect(body).toMatchObject({ error: "Unauthorized" })
  })

  test("health check from non-GET method on /healthz still requires auth", async () => {
    const { status, body } = await makeRequest(port, "/healthz", "POST")

    // POST /healthz does NOT bypass (middleware checks req.method === "GET")
    expect(status).toBe(401)
    expect(body).toMatchObject({ error: "Unauthorized" })
  })
})

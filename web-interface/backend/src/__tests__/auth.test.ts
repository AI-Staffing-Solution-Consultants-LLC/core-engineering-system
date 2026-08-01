import { createHash } from "node:crypto"
import http from "node:http"
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest"
import express from "express"

import { authRouter } from "../routes/auth.js"

// ---------- helpers ----------

function makeRequest(
  port: number,
  path: string,
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
      method: "POST",
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
  app.use("/api/auth", authRouter)

  const server = app.listen(0)
  const address = server.address()
  if (!address || typeof address === "string") {
    throw new Error("Failed to get server port")
  }
  const port = address.port
  return { app, server, port }
}

// ---------- tests ----------

describe("POST /api/auth", () => {
  const CORRECT_PASSWORD = "correct-password"
  const WRONG_PASSWORD = "wrong-password"
  const PASSWORD_HASH = createHash("sha256").update(CORRECT_PASSWORD).digest("hex")

  let port: number
  let server: ReturnType<express.Express["listen"]>

  beforeEach(() => {
    vi.stubEnv("ACCESS_PASSWORD_HASH", PASSWORD_HASH)
    const fixture = buildApp()
    server = fixture.server
    port = fixture.port
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    server.close()
  })

  test("matching password hash returns authenticated:true with token", async () => {
    const { status, body } = await makeRequest(port, "/api/auth", {
      password: CORRECT_PASSWORD,
    })

    expect(status).toBe(200)

    const data = body as Record<string, unknown>
    expect(data["authenticated"]).toBe(true)
    expect(data["token"]).toBeDefined()
    expect(typeof data["token"]).toBe("string")
    // token is a base64 string
    const token = data["token"] as string
    expect(() => Buffer.from(token, "base64").toString("utf-8")).not.toThrow()
  })

  test("wrong password returns authenticated:false with 401 status", async () => {
    const { status, body } = await makeRequest(port, "/api/auth", {
      password: WRONG_PASSWORD,
    })

    expect(status).toBe(401)

    const data = body as Record<string, unknown>
    expect(data["authenticated"]).toBe(false)
    expect(data["token"]).toBeUndefined()
  })

  test("missing password returns 400", async () => {
    const { status, body } = await makeRequest(port, "/api/auth", {})

    expect(status).toBe(400)
    expect(body).toMatchObject({
      error: expect.stringContaining("Missing or invalid 'password'"),
    })
  })

  test("empty string password returns 400", async () => {
    const { status, body } = await makeRequest(port, "/api/auth", { password: "" })

    expect(status).toBe(400)
    expect(body).toMatchObject({
      error: expect.stringContaining("Missing or invalid 'password'"),
    })
  })

  test("numeric password returns 400 (not a string)", async () => {
    const { status, body } = await makeRequest(port, "/api/auth", { password: 12345 })

    expect(status).toBe(400)
    expect(body).toMatchObject({
      error: expect.stringContaining("Missing or invalid 'password'"),
    })
  })
})

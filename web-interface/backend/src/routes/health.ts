import { Router, type Request, type Response } from "express"

const healthRouter = Router()

interface ServiceStatus {
  sheryl: "ok" | "unreachable"
  trackA: "ok" | "unreachable"
  trackB: "ok" | "unreachable"
  telegram: "ok" | "unreachable"
}

interface HealthResponse {
  healthy: boolean
  services: ServiceStatus
}

const PROBE_TIMEOUT_MS = 5000

async function probeService(url: string | undefined, path: string): Promise<"ok" | "unreachable"> {
  if (!url) {
    return "unreachable"
  }

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS)

    const response = await fetch(`${url}${path}`, {
      method: "GET",
      signal: controller.signal,
      headers: { "User-Agent": "web-interface-health-probe/1.0" },
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      return "ok"
    }
    return "unreachable"
  } catch {
    return "unreachable"
  }
}

healthRouter.get("/", async (_req: Request, res: Response): Promise<void> => {
  const [sheryl, trackA, trackB, telegram] = await Promise.all([
    probeService(process.env["SHERYL_URL"], "/healthz"),
    probeService(process.env["TRACK_A_URL"], "/healthz"),
    probeService(process.env["TRACK_B_URL"], "/healthz"),
    probeService(process.env["TELEGRAM_BRIDGE_URL"], "/healthz"),
  ])

  const services: ServiceStatus = { sheryl, trackA, trackB, telegram }
  const healthy = sheryl === "ok" && trackA === "ok" && trackB === "ok" && telegram === "ok"

  const body: HealthResponse = { healthy, services }
  res.json(body)
})

export { healthRouter }

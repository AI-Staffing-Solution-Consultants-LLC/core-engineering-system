import { Router, type Request, type Response } from "express"

import { proxyRequest } from "../middleware/proxy.js"

const commandRouter = Router()

commandRouter.post("/", async (req: Request, res: Response): Promise<void> => {
  const { query } = req.body as { query?: string }
  if (!query || typeof query !== "string" || query.trim().length === 0) {
    res.status(400).json({ error: "Missing or invalid 'query' field in request body" })
    return
  }

  const sherylUrl = process.env["SHERYL_URL"]
  if (!sherylUrl) {
    res.status(500).json({ error: "SHERYL_URL environment variable is not set" })
    return
  }

  try {
    const result = await proxyRequest("POST", `${sherylUrl}/plan`, { query: query.trim() })

    if (!result.ok) {
      const detail = typeof result.data === "string" ? result.data : "Unknown upstream error"
      res.status(502).json({
        error: `Upstream service returned ${result.status}`,
        detail,
      })
      return
    }

    res.json(result.data)
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      res.status(504).json({ error: "Request to upstream service timed out" })
      return
    }
    res.status(502).json({
      error: "Failed to reach upstream service",
      detail: err instanceof Error ? err.message : "Unknown error",
    })
  }
})

export { commandRouter }

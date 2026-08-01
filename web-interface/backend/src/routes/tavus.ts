import { Router, type Request, type Response } from "express"

import { proxyRequest } from "../middleware/proxy.js"
import { validateTavusContext } from "../middleware/tavus-context.js"

const tavusRouter = Router()

tavusRouter.post("/context", async (req: Request, res: Response): Promise<void> => {
  const { conversationId, contextData } = req.body as {
    conversationId?: string
    contextData?: Record<string, unknown>
  }

  if (!conversationId || typeof conversationId !== "string") {
    res.status(400).json({
      error: "Missing or invalid 'conversationId' field in request body",
    })
    return
  }

  if (!contextData || typeof contextData !== "object" || Array.isArray(contextData)) {
    res.status(400).json({
      error: "Missing or invalid 'contextData' field in request body (must be a plain object)",
    })
    return
  }

  const validation = validateTavusContext(contextData)
  if (!validation.valid) {
    res.status(400).json({
      error: `Invalid context data: ${validation.error!}`,
    })
    return
  }

  const apiKey = process.env["TAVUS_API_KEY"]
  if (!apiKey) {
    res.status(500).json({ error: "TAVUS_API_KEY environment variable is not set" })
    return
  }

  const tavusUrl = `https://api.tavus.io/v2/conversations/${conversationId}/context`

  try {
    const result = await proxyRequest("POST", tavusUrl, contextData, {
      Authorization: `Bearer ${apiKey}`,
    })

    if (!result.ok) {
      let detail = "Unknown Tavus API error"
      if (typeof result.data === "string") {
        detail = result.data
      }
      res.status(502).json({
        error: `Tavus API returned ${result.status}`,
        detail,
      })
      return
    }

    res.json(result.data)
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      res.status(504).json({ error: "Request to Tavus API timed out" })
      return
    }
    res.status(502).json({
      error: "Failed to reach Tavus API",
    })
  }
})

export { tavusRouter }

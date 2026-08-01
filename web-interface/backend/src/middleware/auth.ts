import type { Request, Response, NextFunction } from "express"

export function authMiddleware(req: Request, res: Response, next: NextFunction): void {
  // Skip auth for health probe
  if (req.method === "GET" && req.path === "/healthz") {
    next()
    return
  }

  // Skip auth for login endpoint
  if (req.method === "POST" && req.path.startsWith("/api/auth")) {
    next()
    return
  }

  const apiToken = process.env["API_TOKEN"]

  // Dev mode: if API_TOKEN is not set, allow all requests
  if (!apiToken) {
    console.warn("API_TOKEN environment variable is not set — auth disabled (dev mode)")
    next()
    return
  }

  const authHeader = req.headers.authorization
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    res.status(401).json({ error: "Unauthorized" })
    return
  }

  const token = authHeader.slice(7)
  if (token !== apiToken) {
    res.status(401).json({ error: "Unauthorized" })
    return
  }

  next()
}

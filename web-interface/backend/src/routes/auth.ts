import { createHash } from "node:crypto"
import { Router, type Request, type Response } from "express"

const authRouter = Router()

const TOKEN_VALIDITY_MS = 86400000 // 24 hours

function hashPassword(password: string): string {
  return createHash("sha256").update(password).digest("hex")
}

function generateToken(): string {
  const payload = JSON.stringify({ exp: Date.now() + TOKEN_VALIDITY_MS })
  return Buffer.from(payload).toString("base64")
}

interface AuthRequest {
  password?: string
}

interface AuthResponseSuccess {
  authenticated: true
  token: string
}

interface AuthResponseFailure {
  authenticated: false
}

authRouter.post("/", (req: Request, res: Response): void => {
  const { password } = req.body as AuthRequest

  if (!password || typeof password !== "string") {
    res.status(400).json({ error: "Missing or invalid 'password' field in request body" })
    return
  }

  const expectedHash = process.env["ACCESS_PASSWORD_HASH"]
  if (!expectedHash) {
    res.status(500).json({ error: "ACCESS_PASSWORD_HASH environment variable is not set" })
    return
  }

  const inputHash = hashPassword(password)

  if (inputHash === expectedHash) {
    const body: AuthResponseSuccess = { authenticated: true, token: generateToken() }
    res.json(body)
    return
  }

  const body: AuthResponseFailure = { authenticated: false }
  res.status(401).json(body)
})

export { authRouter }

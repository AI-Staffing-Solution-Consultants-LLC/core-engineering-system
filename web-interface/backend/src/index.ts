import cors from "cors"
import express, { type Request, type Response } from "express"

import { authMiddleware } from "./middleware/auth.js"

import { healthRouter } from "./routes/health.js"
import { commandRouter } from "./routes/command.js"
import { telemetryRouter } from "./routes/telemetry.js"
import { tavusRouter } from "./routes/tavus.js"
import { authRouter } from "./routes/auth.js"

const PORT = 3001
const app = express()

app.use(cors({ origin: "http://localhost:3000" }))
app.use(express.json())

app.use(authMiddleware)

app.get("/healthz", (_req: Request, res: Response): void => {
  res.json({ status: "ok", service: "web-interface-backend" })
})

app.use("/api/health", healthRouter)
app.use("/api/command", commandRouter)
app.use("/api/telemetry", telemetryRouter)
app.use("/api/tavus", tavusRouter)
app.use("/api/auth", authRouter)

app.listen(PORT, (): void => {
  console.log(`web-interface-backend listening on port ${PORT}`)
})

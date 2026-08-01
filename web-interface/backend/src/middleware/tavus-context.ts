export interface TavusContextValidation {
  valid: boolean
  error?: string
}

export function validateTavusContext(body: unknown): TavusContextValidation {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return { valid: false, error: "contextData must be a plain object" }
  }

  const record = body as Record<string, unknown>

  for (const [key, value] of Object.entries(record)) {
    if (typeof key !== "string" || key.length === 0) {
      return { valid: false, error: "All context keys must be non-empty strings" }
    }

    if (typeof value === "number") {
      if (value < 0 || value > 1) {
        return {
          valid: false,
          error: `Blendshape value for "${key}" must be between 0 and 1, got ${value}`,
        }
      }
    } else if (typeof value !== "string") {
      return {
        valid: false,
        error: `Value for "${key}" must be a number (0-1) or string, got ${typeof value}`,
      }
    }
  }

  return { valid: true }
}

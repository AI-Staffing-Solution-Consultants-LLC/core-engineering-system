export interface ProxyResult {
  ok: boolean
  status: number
  data: unknown
}

export async function proxyRequest(
  method: string,
  url: string,
  body?: unknown,
  headers?: Record<string, string>,
): Promise<ProxyResult> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 5000)

  try {
    const init: RequestInit = {
      method,
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      signal: controller.signal,
    }
    if (body !== undefined) {
      init.body = JSON.stringify(body)
    }

    const response = await fetch(url, init)

    clearTimeout(timeoutId)

    let data: unknown
    try {
      data = await response.json()
    } catch {
      data = await response.text()
    }

    return { ok: response.ok, status: response.status, data }
  } catch (err) {
    clearTimeout(timeoutId)
    throw err
  }
}

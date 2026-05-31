/**
 * Typed fetch wrapper for the scripture-pattern-lab FastAPI backend.
 *
 * The wrapper lives here (in `server/utils/`) so it runs only on the
 * Cloudflare Worker — never in the browser. The browser cannot see the
 * backend URL or the bearer token under any circumstances; both are
 * server-only secrets read from `useRuntimeConfig()` in the route
 * handler and passed in explicitly here.
 *
 * Errors from the upstream backend propagate to the browser unchanged:
 * the upstream status code is mirrored on the H3 response, and the
 * upstream JSON body (the project's ErrorResponse envelope) is the
 * response body. This lets the frontend dispatch UI off
 * `body.detail.error` consistently whether the error came from the
 * backend (parse_error, validation_unsupported, ...) or the proxy
 * itself (network failure, missing config, etc.).
 */

export interface BackendConfig {
  url: string
  token: string
}

export interface BackendError {
  status: number
  body: unknown
}

export interface ProxyOpts<TReq> {
  config: BackendConfig
  path: string
  body: TReq
  // Optional fetch override for testing.
  fetchImpl?: typeof globalThis.fetch
}

/**
 * Forward a JSON POST to the backend with bearer auth.
 *
 * Throws a `BackendError` on non-2xx responses; caller is expected to
 * translate this into an H3 createError so Nitro mirrors the upstream
 * status + body to the browser.
 */
export async function proxyToBackend<TReq, TRes>(
  opts: ProxyOpts<TReq>,
): Promise<TRes> {
  if (!opts.config.url) {
    throw {
      status: 500,
      body: {
        detail: {
          error: 'backend_misconfigured',
          message: 'NUXT_BACKEND_URL is not set on this Worker',
          details: null,
        },
      },
    } satisfies BackendError
  }

  if (!opts.config.token) {
    throw {
      status: 500,
      body: {
        detail: {
          error: 'backend_misconfigured',
          message: 'NUXT_BACKEND_TOKEN is not set on this Worker',
          details: null,
        },
      },
    } satisfies BackendError
  }

  const fetchFn = opts.fetchImpl ?? globalThis.fetch
  const url = `${opts.config.url.replace(/\/+$/, '')}${opts.path}`

  let response: Response
  try {
    response = await fetchFn(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${opts.config.token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(opts.body),
    })
  } catch {
    // Network-layer failure (DNS, TLS, connection refused). Don't leak
    // raw error text — it can include the upstream URL.
    throw {
      status: 502,
      body: {
        detail: {
          error: 'backend_unreachable',
          message: 'could not reach the backend',
          details: null,
        },
      },
    } satisfies BackendError
  }

  // Pass through the response body for both success and error cases.
  // The backend returns JSON; if it doesn't (very unusual), we surface
  // a generic error rather than crashing.
  let body: unknown
  try {
    body = await response.json()
  } catch {
    throw {
      status: 502,
      body: {
        detail: {
          error: 'backend_response_not_json',
          message: 'backend returned a non-JSON response',
          details: null,
        },
      },
    } satisfies BackendError
  }

  if (!response.ok) {
    throw { status: response.status, body } satisfies BackendError
  }

  return body as TRes
}

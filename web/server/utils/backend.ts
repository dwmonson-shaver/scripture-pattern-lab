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

export interface GetProxyOpts {
  config: BackendConfig
  path: string
  // Optional fetch override for testing.
  fetchImpl?: typeof globalThis.fetch
}

/**
 * Assert the backend URL + token are configured. Both proxy entry points
 * (POST and GET) need the same precondition; pulling it out keeps the
 * error envelope identical regardless of method.
 */
function assertConfigured(config: BackendConfig): void {
  if (!config.url) {
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

  if (!config.token) {
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
}

/**
 * Forward a JSON POST to the backend with bearer auth.
 *
 * Throws a `BackendError` on non-2xx responses; caller is expected to
 * translate this into an H3 createError so Nitro mirrors the upstream
 * status + body to the browser.
 */
export async function proxyToBackend<TReq, TRes>(opts: ProxyOpts<TReq>): Promise<TRes> {
  assertConfigured(opts.config)

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

/**
 * HTTP methods that carry a JSON body. `sendToBackend` accepts these so a
 * single helper covers POST / PATCH / DELETE without duplicating the error
 * contract per verb.
 */
export type WriteMethod = 'POST' | 'PATCH' | 'DELETE'

export interface SendProxyOpts<TReq> {
  config: BackendConfig
  path: string
  method: WriteMethod
  // DELETE often has no body; make it optional.
  body?: TReq
  // Optional fetch override for testing.
  fetchImpl?: typeof globalThis.fetch
}

/**
 * Method-aware sibling of `proxyToBackend` (which is POST-only). Same error
 * contract — throws a `BackendError` on non-2xx so the caller mirrors the
 * upstream status + body via `createError`. Slice 1 (DEC-149): the marks /
 * concepts write paths need PATCH + DELETE, which `proxyToBackend` cannot
 * express. `proxyToBackend` / `getFromBackend` stay intact; this is additive.
 *
 * A 204 (or any empty body) is tolerated — `null` is returned rather than
 * failing the JSON parse, because DELETE responses may carry no content.
 */
export async function sendToBackend<TReq, TRes>(opts: SendProxyOpts<TReq>): Promise<TRes> {
  assertConfigured(opts.config)

  const fetchFn = opts.fetchImpl ?? globalThis.fetch
  const url = `${opts.config.url.replace(/\/+$/, '')}${opts.path}`

  const headers: Record<string, string> = {
    Authorization: `Bearer ${opts.config.token}`,
    Accept: 'application/json',
  }
  const init: RequestInit = { method: opts.method, headers }
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(opts.body)
  }

  let response: Response
  try {
    response = await fetchFn(url, init)
  } catch {
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

  // Read the body as text first so an empty (204) response doesn't blow up the
  // JSON parser; only parse when there's content.
  const text = await response.text()
  let body: unknown = null
  if (text.length > 0) {
    try {
      body = JSON.parse(text)
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
  }

  if (!response.ok) {
    throw { status: response.status, body } satisfies BackendError
  }

  return body as TRes
}

/**
 * Forward a GET to the backend with bearer auth. Same error contract as
 * `proxyToBackend` so the browser sees an identical envelope shape
 * regardless of HTTP verb.
 *
 * Slice N (DEC-106): introduced for `/api/v1/concepts/{name}/document`,
 * the persisted two-part Conceptual Document. The caller is responsible
 * for URL-encoding the path segments inside `path`.
 */
export async function getFromBackend<TRes>(opts: GetProxyOpts): Promise<TRes> {
  assertConfigured(opts.config)

  const fetchFn = opts.fetchImpl ?? globalThis.fetch
  const url = `${opts.config.url.replace(/\/+$/, '')}${opts.path}`

  let response: Response
  try {
    response = await fetchFn(url, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${opts.config.token}`,
        Accept: 'application/json',
      },
    })
  } catch {
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

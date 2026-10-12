/**
 * Formalie portal Worker (production only; wrangler.jsonc). Serves the static build
 * (`.output/public`) on every portal host: `*.formalie.com`, `manage.`, `forms.` and workspaces'
 * verified own domains. It runs first only for:
 *   /api/*                   proxied to the API (API_ORIGIN), so the browser stays same-origin
 *   /s/{code}                short links, answered with a redirect
 *   /{formKey}/fill · embed  index.html with the form's title and link-preview tags
 * Everything else comes straight from the static assets, with the SPA fallback to index.html.
 * The logic lives in edge/lib.ts (pure functions, tested in Node).
 */
import {
  edgeHeaders,
  injectMeta,
  matchRoute,
  pageHeaders,
  parsePreview,
  safeRedirect,
  type FormPreview,
} from './lib'

// Small local declarations instead of @cloudflare/workers-types.
interface Fetcher {
  fetch(request: Request): Promise<Response>
}
export interface Env {
  /** The API's origin, e.g. https://services.formalie.com (a var in wrangler.jsonc). */
  API_ORIGIN: string
  /** Shared with the backend (`wrangler secret put EDGE_SECRET`); proves a request came through the Worker. */
  EDGE_SECRET: string
  /** The static build. */
  ASSETS: Fetcher
}

const PREVIEW_TIMEOUT_MS = 2500

function edgeFor(request: Request, env: Env) {
  const url = new URL(request.url)
  return { host: url.host, ip: request.headers.get('CF-Connecting-IP'), secret: env.EDGE_SECRET }
}

function apiUrl(env: Env, path: string): string {
  return `${env.API_ORIGIN.replace(/\/+$/, '')}${path}`
}

/** `/api/*` → the API: method, query, cookies and body as they are; Set-Cookie and redirects back untouched. */
async function proxyApi(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url)
  const hasBody = request.method !== 'GET' && request.method !== 'HEAD'
  const upstream = await fetch(apiUrl(env, url.pathname + url.search), {
    method: request.method,
    headers: edgeHeaders(request.headers, edgeFor(request, env)),
    body: hasBody ? request.body : null,
    // Sign-in with Google or Facebook answers 302s that the browser itself must follow.
    redirect: 'manual',
  })
  const headers = new Headers(upstream.headers)
  headers.set('Cache-Control', 'no-store')
  return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers })
}

/** A GET to the API's edge endpoints, as JSON; null on any failure (never throws). */
async function edgeGet(
  request: Request,
  env: Env,
  path: string,
): Promise<{ status: number; body: unknown } | null> {
  try {
    const headers = edgeHeaders(new Headers({ Accept: 'application/json' }), edgeFor(request, env))
    const response = await fetch(apiUrl(env, path), {
      headers,
      redirect: 'manual',
      signal: AbortSignal.timeout(PREVIEW_TIMEOUT_MS),
    })
    if (response.status === 404) return { status: 404, body: null }
    if (!response.ok) return null
    return { status: response.status, body: await response.json() }
  } catch {
    return null
  }
}

/** The SPA's index.html from the static build (`/` serves it). */
function indexHtml(request: Request, env: Env): Promise<Response> {
  return env.ASSETS.fetch(new Request(new URL('/', request.url), { headers: { Accept: 'text/html' } }))
}

/** Form pages: index.html with the form's preview tags; plain index.html if the preview isn't there. */
async function formPage(request: Request, env: Env, formKey: string, embed: boolean): Promise<Response> {
  const [asset, answer] = await Promise.all([
    indexHtml(request, env),
    edgeGet(request, env, `/api/v1/edge/forms/${encodeURIComponent(formKey)}/preview`),
  ])
  let html = await asset.text()
  const preview: FormPreview | null = answer?.status === 200 ? parsePreview(answer.body) : null
  if (preview)
    html = injectMeta(html, preview, {
      url: new URL(request.url).origin + new URL(request.url).pathname,
      embed,
    })
  // Unknown forms still get the app (it shows "not found"), with the right status for crawlers.
  return new Response(request.method === 'HEAD' ? null : html, {
    status: answer?.status === 404 ? 404 : 200,
    headers: pageHeaders({ embed, ancestors: preview?.embed_ancestors }),
  })
}

/** Short links: a redirect to the form's current address; otherwise the app's own /s/ page decides. */
async function shortLink(request: Request, env: Env, code: string): Promise<Response> {
  const answer = await edgeGet(request, env, `/api/v1/edge/links/${encodeURIComponent(code)}`)
  const location =
    answer?.status === 200 ? safeRedirect((answer.body as { location?: unknown } | null)?.location) : null
  if (location)
    return new Response(null, { status: 302, headers: { Location: location, 'Cache-Control': 'no-store' } })
  const asset = await indexHtml(request, env)
  return new Response(request.method === 'HEAD' ? null : asset.body, {
    status: answer?.status === 404 ? 404 : 200,
    headers: pageHeaders({ embed: false }),
  })
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const route = matchRoute(new URL(request.url).pathname)
    if (route.kind === 'api') return proxyApi(request, env)
    const page = request.method === 'GET' || request.method === 'HEAD'
    if (page && route.kind === 'short') return shortLink(request, env, route.code)
    if (page && route.kind === 'form') return formPage(request, env, route.formKey, route.mode === 'embed')
    return env.ASSETS.fetch(request)
  },
}

import { afterEach, describe, expect, it, vi } from 'vitest'
import worker, { type Env } from '../../edge/worker'

const shell = '<!DOCTYPE html><html><head><title>Formalie</title></head><body></body></html>'
const env: Env = {
  API_ORIGIN: 'https://services.formalie.com',
  EDGE_SECRET: 'edge-secret',
  ASSETS: {
    fetch: async request =>
      new Response(new URL(request.url).pathname === '/' ? shell : 'asset', {
        headers: { 'Content-Type': 'text/html' },
      }),
  },
}
const visit = (path: string, init: RequestInit = {}) =>
  worker.fetch(
    new Request(`https://acme.formalie.com${path}`, {
      ...init,
      headers: { 'CF-Connecting-IP': '203.0.113.7', ...(init.headers as Record<string, string>) },
    }),
    env,
  )

afterEach(() => vi.unstubAllGlobals())

describe('Worker', () => {
  it('proxies /api with the edge headers, passing redirects and cookies back', async () => {
    const calls: { url: string; init: RequestInit }[] = []
    vi.stubGlobal('fetch', async (url: string, init: RequestInit) => {
      calls.push({ url, init })
      const headers = new Headers({ Location: 'https://accounts.google.com/o/oauth2' })
      headers.append('Set-Cookie', 'a=1; HttpOnly')
      headers.append('Set-Cookie', 'b=2; HttpOnly')
      return new Response(null, { status: 302, headers })
    })
    const response = await visit('/api/v1/auth/oauth/google/start?next=%2F', {
      headers: { 'X-Formalie-Edge': 'guess', Cookie: 'c=3' },
    })
    expect(calls[0]!.url).toBe('https://services.formalie.com/api/v1/auth/oauth/google/start?next=%2F')
    expect(calls[0]!.init.redirect).toBe('manual')
    const sent = calls[0]!.init.headers as Headers
    expect(sent.get('x-formalie-edge')).toBe('edge-secret')
    expect(sent.get('x-forwarded-host')).toBe('acme.formalie.com')
    expect(sent.get('x-forwarded-for')).toBe('203.0.113.7')
    expect(sent.get('cookie')).toBe('c=3')
    expect(response.status).toBe(302)
    expect(response.headers.get('location')).toBe('https://accounts.google.com/o/oauth2')
    expect(response.headers.getSetCookie()).toEqual(['a=1; HttpOnly', 'b=2; HttpOnly'])
    expect(response.headers.get('cache-control')).toBe('no-store')
  })

  it('redirects a short link', async () => {
    vi.stubGlobal('fetch', async () =>
      Response.json({ location: 'https://forms.formalie.com/Ab3dEf9hJk/fill' }),
    )
    const response = await visit('/s/ab3kz')
    expect(response.status).toBe(302)
    expect(response.headers.get('location')).toBe('https://forms.formalie.com/Ab3dEf9hJk/fill')
  })

  it('serves the app for an unknown short link', async () => {
    vi.stubGlobal('fetch', async () => new Response(null, { status: 404 }))
    const response = await visit('/s/ab3kz')
    expect(response.status).toBe(404)
    expect(await response.text()).toBe(shell)
  })

  it('adds the preview tags to a form page', async () => {
    vi.stubGlobal('fetch', async () =>
      Response.json({
        title: 'Survey',
        description: null,
        image_url: null,
        language: 'de',
        indexable: true,
        site_name: 'Acme',
      }),
    )
    const response = await visit('/Ab3dEf9hJk/fill')
    const html = await response.text()
    expect(response.status).toBe(200)
    expect(html).toContain('<title>Survey · Acme</title>')
    expect(html).toContain('lang="de"')
    expect(response.headers.get('x-frame-options')).toBe('SAMEORIGIN')
  })

  it('serves the plain page when the preview fails, never an error page', async () => {
    vi.stubGlobal('fetch', async () => {
      throw new Error('down')
    })
    const response = await visit('/Ab3dEf9hJk/embed')
    expect(response.status).toBe(200)
    expect(await response.text()).toBe(shell)
    expect(response.headers.has('x-frame-options')).toBe(false)
  })

  it('hands every other path to the static build', async () => {
    const response = await visit('/forms')
    expect(await response.text()).toBe('asset')
  })
})

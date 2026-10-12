import { readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  edgeHeaders,
  escapeHtml,
  frameAncestors,
  injectMeta,
  isSpoofable,
  matchRoute,
  pageHeaders,
  parsePreview,
  safeImageUrl,
  safeRedirect,
  type FormPreview,
} from '../../edge/lib'
import { headersFile } from '../../edge/security-headers'
import { RESERVED_LINKS } from '#shared/utils/urls/public'

const edge = { host: 'acme.formalie.com', ip: '203.0.113.7', secret: 'edge-secret' }

describe('edgeHeaders', () => {
  it('drops headers a visitor could spoof and sets the edge ones', () => {
    const incoming = new Headers({
      'X-Formalie-Edge': 'guessed',
      'X-Forwarded-Host': 'other.formalie.com',
      'X-Forwarded-For': '10.0.0.1',
      'X-Forwarded-Proto': 'http',
      'X-Forwarded-Port': '80',
      Forwarded: 'for=10.0.0.1;host=evil.example',
      'CF-Connecting-IP': '10.0.0.2',
      'CF-IPCountry': 'XX',
      'X-Real-IP': '10.0.0.3',
      'True-Client-IP': '10.0.0.4',
      Host: 'evil.example',
      Cookie: 'formalie_refresh=abc',
      'Content-Type': 'application/json',
      'X-CSRF-Token': 'csrf',
    })
    const out = edgeHeaders(incoming, edge)
    expect(out.get('x-formalie-edge')).toBe('edge-secret')
    expect(out.get('x-forwarded-host')).toBe('acme.formalie.com')
    expect(out.get('x-forwarded-proto')).toBe('https')
    expect(out.get('x-forwarded-for')).toBe('203.0.113.7')
    for (const name of [
      'x-forwarded-port',
      'forwarded',
      'cf-connecting-ip',
      'cf-ipcountry',
      'x-real-ip',
      'true-client-ip',
      'host',
    ])
      expect(out.has(name)).toBe(false)
    expect(out.get('cookie')).toBe('formalie_refresh=abc')
    expect(out.get('content-type')).toBe('application/json')
    expect(out.get('x-csrf-token')).toBe('csrf')
  })

  it('leaves X-Forwarded-For out when Cloudflare gave no address', () => {
    expect(
      edgeHeaders(new Headers({ 'X-Forwarded-For': '1.2.3.4' }), { ...edge, ip: null }).has(
        'x-forwarded-for',
      ),
    ).toBe(false)
  })

  it('knows which names are spoofable', () => {
    expect(isSpoofable('X-FORWARDED-anything')).toBe(true)
    expect(isSpoofable('cf-ray')).toBe(true)
    expect(isSpoofable('Authorization')).toBe(false)
  })
})

describe('matchRoute', () => {
  it('finds the paths the Worker answers', () => {
    expect(matchRoute('/api/v1/auth/me')).toEqual({ kind: 'api' })
    expect(matchRoute('/s/ab3kz')).toEqual({ kind: 'short', code: 'ab3kz' })
    expect(matchRoute('/Ab3dEf9hJk/fill')).toEqual({ kind: 'form', formKey: 'Ab3dEf9hJk', mode: 'fill' })
    expect(matchRoute('/procurement-request/embed')).toEqual({
      kind: 'form',
      formKey: 'procurement-request',
      mode: 'embed',
    })
  })

  it('leaves app routes and anything else to the static build', () => {
    for (const path of [
      '/',
      '/forms',
      '/folders/fill',
      '/people/embed',
      '/forms/abc/fill',
      '/s/0000l',
      '/s/ab3kz/x',
      '/apix',
      '/Ab3dEf9hJk/fill/x',
      '/a/fill',
      '/Bad_Key!!/fill',
    ])
      expect(matchRoute(path), path).toEqual({ kind: 'asset' })
  })

  it('reserves every top-level page of the app', () => {
    const pages = fileURLToPath(new URL('../../app/pages', import.meta.url))
    const names = readdirSync(pages)
      .map(name => name.replace(/\.vue$/, ''))
      .filter(name => name !== 'index' && !name.startsWith('['))
    for (const name of names) expect(RESERVED_LINKS.has(name), name).toBe(true)
  })
})

const preview: FormPreview = {
  title: 'Job application',
  description: 'Apply in five minutes',
  image_url: 'https://cdn.example.com/cover.png',
  language: 'fr',
  indexable: true,
  site_name: 'Acme',
}
const shell =
  '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Formalie</title></head><body><div id="__nuxt"></div></body></html>'

describe('injectMeta', () => {
  it('sets the title, preview tags and language', () => {
    const html = injectMeta(shell, preview, {
      url: 'https://acme.formalie.com/Ab3dEf9hJk/fill',
      embed: false,
    })
    expect(html).toContain('<title>Job application · Acme</title>')
    expect(html).not.toContain('<title>Formalie</title>')
    expect(html).toContain('<meta property="og:title" content="Job application">')
    expect(html).toContain('<meta property="og:description" content="Apply in five minutes">')
    expect(html).toContain('<meta property="og:image" content="https://cdn.example.com/cover.png">')
    expect(html).toContain('<meta property="og:site_name" content="Acme">')
    expect(html).toContain('<meta name="twitter:card" content="summary_large_image">')
    expect(html).toContain('<html lang="fr">')
    expect(html).not.toContain('noindex')
  })

  it('escapes every value, including a title that tries to break out', () => {
    const html = injectMeta(
      shell,
      { ...preview, title: '"<script>alert(1)</script>', description: "it's <b>", site_name: 'A&B' },
      { url: 'https://x.formalie.com/k/fill?a="b"', embed: false },
    )
    expect(html).not.toContain('<script>alert')
    expect(html).toContain('<title>&quot;&lt;script&gt;alert(1)&lt;/script&gt; · A&amp;B</title>')
    expect(html).toContain('content="&quot;&lt;script&gt;alert(1)&lt;/script&gt;"')
    expect(html).toContain('content="it&#39;s &lt;b&gt;"')
    expect(html).toContain('content="https://x.formalie.com/k/fill?a=&quot;b&quot;"')
  })

  it('drops an image that is not https', () => {
    for (const image of [
      'http://cdn.example.com/a.png',
      'javascript:alert(1)',
      'data:image/png;base64,AAAA',
      '//cdn.example.com/a.png',
    ]) {
      const parsed = parsePreview({ ...preview, image_url: image })!
      expect(parsed.image_url).toBeNull()
      const html = injectMeta(
        shell,
        { ...preview, image_url: image },
        { url: 'https://a.formalie.com/k/fill', embed: false },
      )
      expect(html).not.toContain('og:image')
      expect(html).toContain('<meta name="twitter:card" content="summary">')
    }
    expect(safeImageUrl('https://cdn.example.com/a.png')).toBe('https://cdn.example.com/a.png')
  })

  it('adds noindex when the form is not indexable, and always on embeds', () => {
    expect(
      injectMeta(
        shell,
        { ...preview, indexable: false },
        { url: 'https://a.formalie.com/k/fill', embed: false },
      ),
    ).toContain('<meta name="robots" content="noindex">')
    expect(injectMeta(shell, preview, { url: 'https://a.formalie.com/k/embed', embed: true })).toContain(
      '<meta name="robots" content="noindex">',
    )
  })

  it('replaces an existing lang and copes with a page without a title', () => {
    const html = injectMeta('<html lang="en" class="x"><head></head><body></body></html>', preview, {
      url: 'https://a.formalie.com/k/fill',
      embed: false,
    })
    expect(html).toContain('<html class="x" lang="fr">')
    expect(html).toContain('<head><title>Job application · Acme</title><meta property="og:title"')
  })
})

describe('parsePreview', () => {
  it('refuses answers without a title and cleans odd fields', () => {
    expect(parsePreview(null)).toBeNull()
    expect(parsePreview({ title: '' })).toBeNull()
    const parsed = parsePreview({ title: 'T', language: 'en"><script>', indexable: 'yes', description: 5 })!
    expect(parsed.language).toBe('en')
    expect(parsed.indexable).toBe(false)
    expect(parsed.description).toBeNull()
  })
})

describe('page headers', () => {
  it('keeps the frame rules on pages and opens embeds to their websites', () => {
    const page = pageHeaders({ embed: false })
    expect(page.get('x-frame-options')).toBe('SAMEORIGIN')
    expect(page.get('content-security-policy')).toContain("frame-ancestors 'self'")
    const embed = pageHeaders({
      embed: true,
      ancestors: "'self' https://*.example.com https://shop.example.org",
    })
    expect(embed.has('x-frame-options')).toBe(false)
    expect(embed.get('content-security-policy')).toContain(
      "frame-ancestors 'self' https://*.example.com https://shop.example.org",
    )
    expect(pageHeaders({ embed: true }).get('content-security-policy')).toContain('frame-ancestors *')
  })

  it('never lets a website list inject other rules', () => {
    expect(frameAncestors('https://a.example.com; script-src *')).toBe("'self'")
    expect(frameAncestors('javascript:alert(1)')).toBe("'self'")
    expect(frameAncestors('')).toBe('*')
  })

  it('writes the same headers into the static build', () => {
    expect(headersFile()).toMatch(/^\/\*\n {2}Strict-Transport-Security: /)
    expect(headersFile()).toContain('X-Frame-Options: SAMEORIGIN')
  })
})

describe('short link destinations', () => {
  it('follows only https addresses', () => {
    expect(safeRedirect('https://forms.formalie.com/Ab3dEf9hJk/fill')).toBe(
      'https://forms.formalie.com/Ab3dEf9hJk/fill',
    )
    expect(safeRedirect('javascript:alert(1)')).toBeNull()
    expect(safeRedirect('http://forms.formalie.com/x/fill')).toBeNull()
    expect(safeRedirect('/relative')).toBeNull()
  })
})

describe('escapeHtml', () => {
  it('escapes the five HTML characters', () => {
    expect(escapeHtml(`<a href="x">'&'</a>`)).toBe('&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;')
  })
})

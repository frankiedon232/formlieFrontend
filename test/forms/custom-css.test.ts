import { describe, expect, it } from 'vitest'
import { CSS_SCOPE, CUSTOM_CSS_MAX, sanitiseCss } from '../../shared/utils/forms/custom-css'

const kinds = (input: string) => sanitiseCss(input).issues.map(issue => issue.kind)

describe('custom CSS (leftovers L5)', () => {
  it('keeps ordinary styles, fenced to the form box', () => {
    const { css, issues } = sanitiseCss('h2 { color: #333; letter-spacing: .02em }\n.question, label:hover { font-weight: 600 !important; }')
    expect(issues).toEqual([])
    expect(css).toBe(`${CSS_SCOPE} h2 { color: #333; letter-spacing: .02em }\n${CSS_SCOPE} .question, ${CSS_SCOPE} label:hover { font-weight: 600 !important }`)
  })

  it('turns :root, html and body into the form box itself', () => {
    expect(sanitiseCss(':root { --x: 1px }').css).toBe(`${CSS_SCOPE} { --x: 1px }`)
    expect(sanitiseCss('html body .a { color: red }').css).toBe(`${CSS_SCOPE} .a { color: red }`)
    expect(sanitiseCss('body.dark p { color: red }').css).toBe(`${CSS_SCOPE}.dark p { color: red }`)
  })

  it('keeps @media, @supports and @container with their rules fenced', () => {
    const { css } = sanitiseCss('@media (max-width: 600px) { h2 { font-size: 18px } }')
    expect(css).toBe(`@media (max-width: 600px) {\n${CSS_SCOPE} h2 { font-size: 18px }\n}`)
  })

  it('leaves out anything that loads from elsewhere', () => {
    expect(kinds('@import url("https://evil.example/x.css");')).toEqual(['loads'])
    expect(kinds("@import 'https://evil.example/x.css';")).toEqual(['loads'])
    expect(sanitiseCss('p { background: url(https://tracker.example/p.gif) }').css).toBe('')
    expect(kinds('p { background-image: image-set("a.png" 1x) }')).toEqual(['loads'])
    expect(kinds('@font-face { font-family: x; src: url(x.woff) }')).toEqual(['at_rule'])
    expect(kinds('@keyframes spin { to { transform: rotate(1turn) } }')).toEqual(['at_rule'])
  })

  it('leaves out script-like values and escapes that could hide them', () => {
    expect(kinds('p { width: expression(alert(1)) }')).toEqual(['script'])
    expect(kinds('p { behavior: url(x.htc) }')).toEqual(['script'])
    expect(kinds('p { -moz-binding: url(x.xml#a) }')).toEqual(['script'])
    // "\75 rl(" is url( spelled with an escape
    const escaped = sanitiseCss('p { background: \\75 rl(https://tracker.example/p.gif) } h2 { color: red }')
    expect(escaped.css).not.toMatch(/tracker|\\/)
    expect(escaped.issues.map(issue => issue.kind)).toContain('escape')
  })

  it('never lets the style element be closed, nor the form cover the page', () => {
    const closed = sanitiseCss('p { color: red }</style><script>alert(1)</script>')
    expect(closed.css).not.toContain('<')
    expect(closed.issues.map(issue => issue.kind)).toContain('html')
    expect(kinds('.x { position: fixed; inset: 0 }')).toEqual(['fixed'])
    expect(sanitiseCss('.x { position: fixed; inset: 0 }').css).toBe(`${CSS_SCOPE} .x { inset: 0 }`)
  })

  it('drops comments, broken pieces and too much', () => {
    expect(sanitiseCss('/* note */ p { color: red } /* url(x) */').css).toBe(`${CSS_SCOPE} p { color: red }`)
    expect(kinds('p { color red }')).toEqual(['syntax'])
    expect(kinds('p { color: red')).toEqual(['syntax'])
    expect(sanitiseCss('x'.repeat(CUSTOM_CSS_MAX + 1))).toEqual({ css: '', issues: [{ kind: 'too_long', text: String(CUSTOM_CSS_MAX + 1) }] })
    const many = Array.from({ length: 501 }, (_, i) => `.r${i} { color: red }`).join('\n')
    expect(kinds(many)).toEqual(['too_many'])
    expect(sanitiseCss('')).toEqual({ css: '', issues: [] })
  })

  it('is stable: cleaning clean CSS again changes nothing', () => {
    const once = sanitiseCss('@media (min-width: 40rem) { .a, .b { color: red; margin: 0 auto } }').css
    // Already fenced selectors are fenced again, so the server stores the input, never its own output
    expect(sanitiseCss(once).issues).toEqual([])
  })
})

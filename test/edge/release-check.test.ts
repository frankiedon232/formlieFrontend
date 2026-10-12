import { describe, expect, it } from 'vitest'
// @ts-expect-error a plain .mjs script without type declarations
import { findHits } from '../../scripts/release-check.mjs'

type Hit = { file: string; label: string; context: string }
const labels = (text: string) => (findHits(text, 'x.js') as Hit[]).map(hit => hit.label)

describe('release check', () => {
  it('finds development addresses', () => {
    expect(labels('fetch("https://manage.formalie.dev:2202/api")')).toEqual(['formalie.dev', ':2202'])
    expect(labels('const a="https://formalie.dev:5004";const b="http://localhost:3033"')).toEqual([
      'formalie.dev',
      ':3033',
      ':5004',
      'localhost',
    ])
    expect(labels('x="http://127.0.0.1:5005/v1"')).toEqual([':5005', '127.0.0.1'])
    expect(labels('ca="C:/devcerts/rootCA.pem";tool="mkcert"')).toEqual(['mkcert', 'devcerts'])
    expect(labels('host:"FORMALIE.DEV"')).toEqual(['formalie.dev'])
  })

  it('passes a clean production build', () => {
    expect(
      labels(
        'rootDomain:"formalie.com",formsHost:"forms.formalie.com",apiServiceUrl:"https://api.formalie.com",apiBase:"/api/v1"',
      ),
    ).toEqual([])
    expect(labels('a:22020;b:50041')).toEqual([])
  })

  it('ignores only the explained host-name checks', () => {
    expect(
      labels('n.hostname===`localhost`||n.hostname===`127.0.0.1`||n.hostname.endsWith(`.localhost`)'),
    ).toEqual([])
    expect(labels("new Set(['localhost','127.0.0.1'])")).toEqual([])
    expect(labels(String.raw`wn=/^(localhost|127\.0\.0\.1)$/`)).toEqual([])
    expect(labels('LOCALHOST:Xb')).toEqual([])
    // An address stays a hit even next to a quote
    expect(labels('"http://localhost"')).toEqual(['localhost'])
    expect(labels('`localhost:2202`')).toEqual([':2202', 'localhost'])
  })
})

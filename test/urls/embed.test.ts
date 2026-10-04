import { describe, expect, it } from 'vitest'
import { clampEmbedHeight, embedCode } from '../../shared/utils/urls/embed'

describe('embed code', () => {
  const url = 'https://forms.formalie.com/Ab3dEf7hJk/embed'

  it('auto height: frame + resize script limited to the form origin', () => {
    const code = embedCode({ url, title: 'Event "sign-up"', height: 'auto' })
    expect(code).toContain(`src="${url}"`)
    expect(code).toContain('title="Event &quot;sign-up&quot;"')
    expect(code).toContain('data-formalie-embed')
    expect(code).toContain('e.origin!=="https://forms.formalie.com"')
    expect(code).toContain('formalie:resize')
  })

  it('fixed height: frame only', () => {
    const code = embedCode({ url, title: 'Form', height: 900 })
    expect(code).toContain('height="900"')
    expect(code).not.toContain('<script>')
  })

  it('keeps heights sensible', () => {
    expect(clampEmbedHeight(10)).toBe(240)
    expect(clampEmbedHeight(99999)).toBe(4000)
    expect(clampEmbedHeight(Number.NaN)).toBe(600)
  })
})

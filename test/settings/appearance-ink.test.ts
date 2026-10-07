import { describe, expect, it } from 'vitest'
import { APP_INK, appearanceInk } from '../../shared/utils/settings/appearance-ink'

describe('the workspace colour in exported files', () => {
  it('follows Appearance', () => {
    expect(appearanceInk({ primary: 'mono' })).toBe(APP_INK)
    expect(appearanceInk({ primary: 'green' })).toBe('#16a34a')
    expect(appearanceInk({ primary: 'brand' }, '#0a7cff')).toBe('#0a7cff')
  })

  it('falls back to the ink without a usable colour', () => {
    expect(appearanceInk(null)).toBe(APP_INK)
    expect(appearanceInk({ primary: 'brand' }, null)).toBe(APP_INK)
    expect(appearanceInk({ primary: 'brand' }, 'red')).toBe(APP_INK)
  })
})

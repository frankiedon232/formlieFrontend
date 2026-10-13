import { describe, expect, it } from 'vitest'
import { FALLBACK_PLATFORM, parsePlatform } from '../app/utils/platform'

describe('parsePlatform', () => {
  it('reads the live answer', () => {
    const platform = parsePlatform({
      success: true,
      data: {
        support_email: 'help@formalie.com',
        sales_email: 'sales@formalie.com',
        status_url: 'https://status.formalie.com',
        social: {
          linkedin: 'https://www.linkedin.com/company/formalie',
          x: 'http://x.com/formalie',
          myspace: 'https://a.b',
        },
        legal_entity: { name: 'Formalie Ltd', address: null },
      },
    })
    expect(platform?.supportEmail).toBe('help@formalie.com')
    expect(platform?.statusUrl).toBe('https://status.formalie.com')
    // Unknown networks and plain http links are dropped.
    expect(platform?.social).toEqual([
      { network: 'linkedin', url: 'https://www.linkedin.com/company/formalie' },
    ])
    expect(platform?.legalEntity).toEqual({ name: 'Formalie Ltd', address: null })
  })

  it('keeps the defaults for bad fields and rejects non-answers', () => {
    const platform = parsePlatform({
      data: {
        support_email: 'nope',
        sales_email: null,
        status_url: 'javascript:x',
        social: [],
        legal_entity: { name: '' },
      },
    })
    expect(platform).toEqual({ ...FALLBACK_PLATFORM })
    expect(parsePlatform(null)).toBeNull()
    expect(parsePlatform({ success: false })).toBeNull()
  })
})

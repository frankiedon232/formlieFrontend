import { describe, expect, it } from 'vitest'
import { blankSchema } from '../../shared/utils/forms/build'
import { formSchemaV1 } from '../../shared/utils/forms/schema'

const withRedirect = (redirect_url: string | null) => ({ ...blankSchema(), thank_you: { redirect_url } })

describe('thank-you redirect (web addresses only, as the backend checks)', () => {
  it('takes http and https addresses, or none', () => {
    expect(formSchemaV1.safeParse(withRedirect('https://example.com/thanks')).success).toBe(true)
    expect(formSchemaV1.safeParse(withRedirect('http://example.com')).success).toBe(true)
    expect(formSchemaV1.safeParse(withRedirect(null)).success).toBe(true)
  })

  it('refuses scripts, mail links and other schemes', () => {
    for (const address of ['javascript:alert(1)', 'mailto:someone@example.com', 'data:text/html,hi', 'ftp://example.com']) {
      expect(formSchemaV1.safeParse(withRedirect(address)).success, address).toBe(false)
    }
  })
})

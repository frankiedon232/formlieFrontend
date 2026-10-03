import { describe, expect, it } from 'vitest'
import type { FormField } from '../../shared/utils/forms/build'
import type { FormSchemaV1 } from '../../shared/utils/forms/schema'
import { identityOf, maskEmail, matchIdentity, nameSimilarity, normaliseEmail, normaliseId, suggestEmailField } from '../../shared/utils/forms/identity'

const field = (key: string, type: string, label: string) => ({ id: `f_${key}`, key, type, label, width: 12, required: false }) as FormField
const schemaWith = (fields: FormField[], identity?: FormSchemaV1['settings']) =>
  ({ schema_version: 1, settings: identity, pages: [{ id: 'p1', rows: [{ id: 'r1', fields }] }], logic: [], calculations: [] }) as unknown as FormSchemaV1

const REGISTRATION = schemaWith([
  field('first_name', 'short_text', 'First name'),
  field('last_name', 'short_text', 'Last name'),
  field('email', 'email', 'Email'),
  field('manager_email', 'email', 'Manager’s email'),
  field('phone', 'phone', 'Phone'),
])
const earlier = (data: Record<string, unknown>, id = 'r1') => ({ id, submitted_at: '2026-10-03T19:33:20Z', data })

describe('telling respondents apart', () => {
  it('uses the respondent’s own email, never someone else’s', () => {
    expect(identityOf(REGISTRATION).email).toBe('email')
    expect(suggestEmailField([field('manager_email', 'email', 'Manager’s email'), field('my_email', 'email', 'Your email')])).toBe('my_email')
    expect(suggestEmailField([field('reference_email', 'email', 'Referee email')])).toBeNull()
  })

  it('normalises emails and IDs', () => {
    expect(normaliseEmail(' Ada.Lovelace+forms@GMAIL.com ')).toBe('adalovelace@gmail.com')
    expect(normaliseEmail('ada.lovelace@yahoo.com')).toBe('ada.lovelace@yahoo.com')
    expect(normaliseId('ab-123 456')).toBe('AB123456')
  })

  it('refuses the same email, written differently', () => {
    const match = matchIdentity(REGISTRATION, { email: 'SamuelMark@Yahoo.com' }, [earlier({ email: 'samuelmark@yahoo.com' })])
    expect(match).toMatchObject({ level: 'clear', reason: 'email' })
  })

  it('flags the owner’s case: same name, email one letter apart', () => {
    const match = matchIdentity(
      REGISTRATION,
      { first_name: 'Samual', last_name: 'Mark', email: 'samualmark@yahoo.com', phone: '02548784' },
      [earlier({ first_name: 'Samual', last_name: 'Mark', email: 'samuelmark@yahoo.com', phone: '01225458' })],
    )
    expect(match).toMatchObject({ level: 'likely', reason: 'email_similar' })
  })

  it('does not mistake a different person for an earlier one', () => {
    // Similar email, but clearly another name.
    expect(
      matchIdentity(REGISTRATION, { first_name: 'Amira', last_name: 'Haddad', email: 'samualmarks@yahoo.com' }, [
        earlier({ first_name: 'Samual', last_name: 'Mark', email: 'samuelmark@yahoo.com' }),
      ]).level,
    ).toBe('none')
    // Same family, different person and email.
    expect(
      matchIdentity(REGISTRATION, { first_name: 'Lena', last_name: 'Mark', email: 'lena.mark@example.org' }, [
        earlier({ first_name: 'Samual', last_name: 'Mark', email: 'samuelmark@yahoo.com' }),
      ]).level,
    ).toBe('none')
  })

  it('treats an ID / account number like an email', () => {
    const withId = schemaWith([field('full_name', 'full_name', 'Full name'), field('member_number', 'short_text', 'Membership number')])
    expect(identityOf(withId).id).toBe('member_number')
    expect(matchIdentity(withId, { member_number: 'm-10234' }, [earlier({ member_number: 'M10234' })]).level).toBe('clear')
    expect(matchIdentity(withId, { full_name: 'Ada Lovelace', member_number: 'M10235' }, [earlier({ full_name: 'Ada Lovelace', member_number: 'M10234' })]).level).toBe('likely')
  })

  it('needs an email or an ID to compare people at all', () => {
    const plain = schemaWith([field('comment', 'long_text', 'Comment')])
    expect(identityOf(plain)).toEqual({ email: null, id: null, verify: false })
    expect(matchIdentity(plain, { comment: 'hi' }, [earlier({ comment: 'hi' })]).level).toBe('none')
  })

  it('masks emails in messages and compares names kindly', () => {
    expect(maskEmail('samuelmark@yahoo.com')).toBe('sa•••@yahoo.com')
    expect(nameSimilarity('Mark Samual', 'Samual Mark')).toBe(1)
    expect(nameSimilarity('José Núñez', 'jose nunez')).toBe(1)
  })
})

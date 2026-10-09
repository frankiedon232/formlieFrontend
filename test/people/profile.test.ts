import { describe, expect, it } from 'vitest'
import { profileShare } from '../../app/utils/people/profile'

const base = { departments: [], job_titles: [], phone: null, two_step: false, manager: null, role: 'member' as const }

describe('people profile (F16)', () => {
  it('counts department, job title, phone, two-step and a manager', () => {
    expect(profileShare(base)).toBe(0)
    expect(profileShare({ ...base, departments: [{ id: 'd', name: 'D' }], two_step: true })).toBeCloseTo(2 / 5)
  })
  it('owners need no manager', () => {
    expect(profileShare({ ...base, role: 'owner', departments: [{ id: 'd', name: 'D' }], job_titles: [{ id: 'j', name: 'J' }], phone: '+44 7700 900001', two_step: true })).toBe(1)
  })
})

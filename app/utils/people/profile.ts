import type { PersonRow } from '#shared/types/people'

/**
 * How complete a person's profile is (F16), 0 to 1: department, job title, phone, two-step sign-in and,
 * for everyone but owners, a manager. Shown on the person's card and detail as a slim bar.
 */
export function profileShare(person: Pick<PersonRow, 'departments' | 'job_titles' | 'phone' | 'two_step' | 'manager' | 'role'>): number {
  const checks = [person.departments.length > 0, person.job_titles.length > 0, !!person.phone, person.two_step, ...(person.role === 'owner' ? [] : [!!person.manager])]
  return checks.filter(Boolean).length / checks.length
}

import { describe, expect, it } from 'vitest'
import { ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS, permissionFor, withNeeds } from '../../shared/utils/auth/permissions'

describe('roles & access (F22)', () => {
  it('maps calls to the permission they need', () => {
    expect(permissionFor('GET', '/forms')).toBe('forms.view')
    expect(permissionFor('POST', '/forms')).toBe('forms.create')
    expect(permissionFor('POST', '/forms/f1/publish')).toBe('forms.publish')
    expect(permissionFor('DELETE', '/forms/f1')).toBe('forms.delete')
    expect(permissionFor('PUT', '/forms/f1/draft')).toBe('forms.edit')
    expect(permissionFor('GET', '/forms/f1/responses')).toBe('responses.view')
    expect(permissionFor('POST', '/forms/f1/responses/export')).toBe('responses.export')
    expect(permissionFor('DELETE', '/responses/r1')).toBe('responses.delete')
    expect(permissionFor('POST', '/datasources/d1/query')).toBe('data.query')
    expect(permissionFor('PATCH', '/roles/r1')).toBe('roles.manage')
    expect(permissionFor('GET', '/roles')).toBe('people.view')
    expect(permissionFor('PATCH', '/settings/appearance')).toBe('settings.manage')
    expect(permissionFor('GET', '/audit-logs')).toBe('audit.view')
  })
  it('splits reviewing responses from editing answers', () => {
    expect(permissionFor('PATCH', '/responses/r1')).toBe('responses.review')
    expect(permissionFor('POST', '/responses/r1/notes')).toBe('responses.review')
    expect(permissionFor('POST', '/responses/bulk')).toBe('responses.review')
    // Opening a file is reading
    expect(permissionFor('POST', '/responses/r1/files')).toBe('responses.view')
    expect(withNeeds(['responses.review'])).toEqual(['responses.view', 'responses.review'])
    expect(DEFAULT_ROLE_PERMISSIONS.member).toEqual(expect.arrayContaining(['responses.review', 'responses.edit']))
  })
  it('leaves what every signed-in person needs open', () => {
    for (const path of ['/me/profile', '/navigation/counts', '/directory', '/settings/appearance', '/themes', '/option-lists/l1/options', '/notifications'])
      expect(permissionFor('GET', path), path).toBeNull()
  })
  it('adds what a permission needs, and Owner holds everything', () => {
    expect(withNeeds(['forms.publish'])).toEqual(['forms.view', 'forms.edit', 'forms.publish'])
    expect(withNeeds(['responses.export', 'nonsense'])).toEqual(['responses.view', 'responses.export'])
    expect(DEFAULT_ROLE_PERMISSIONS.owner).toEqual(ALL_PERMISSIONS)
    expect(DEFAULT_ROLE_PERMISSIONS.admin).not.toContain('roles.manage')
  })
})

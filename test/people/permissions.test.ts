import { describe, expect, it } from 'vitest'
import { ALL_GRANTS, ALL_PERMISSIONS, DEFAULT_ROLE_GRANTS, grantsFromList, permissionFor, reachOf, setGrant, withNeeds } from '../../shared/utils/auth/permissions'

describe('roles & access (F22)', () => {
  it('maps calls to the permission they need', () => {
    expect(permissionFor('GET', '/forms')).toBe('forms.view')
    expect(permissionFor('POST', '/forms')).toBe('forms.create')
    expect(permissionFor('POST', '/forms/import')).toBe('forms.import')
    expect(permissionFor('POST', '/forms/f1/duplicate')).toBe('forms.duplicate')
    expect(permissionFor('POST', '/forms/f1/publish')).toBe('forms.publish')
    expect(permissionFor('DELETE', '/forms/trash')).toBe('forms.purge')
    // Other form calls only need "works with forms"; the route checks its own action on the form
    expect(permissionFor('PATCH', '/forms/f1')).toBe('forms.view')
    expect(permissionFor('POST', '/forms/f1/archive')).toBe('forms.view')
    // Opening an organisation-only form is not editing
    expect(permissionFor('POST', '/forms/pass')).toBeNull()
    expect(permissionFor('GET', '/forms/f1/responses')).toBe('responses.view')
    expect(permissionFor('POST', '/forms/f1/responses/export')).toBe('responses.export')
    expect(permissionFor('DELETE', '/responses/r1')).toBe('responses.delete')
    expect(permissionFor('POST', '/folders')).toBe('folders.create')
    expect(permissionFor('PATCH', '/folders/x1')).toBe('folders.edit')
    expect(permissionFor('DELETE', '/folders/x1')).toBe('folders.delete')
    expect(permissionFor('PUT', '/folders/x1/access')).toBe('folders.access')
    expect(permissionFor('GET', '/folders/overview')).toBeNull()
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
    expect(withNeeds({ 'responses.review': 'all' })).toEqual({ 'responses.view': 'all', 'responses.review': 'all' })
    // Responses have a reach too (F22 R2 M2): Member works with responses of their own and shared forms
    expect(DEFAULT_ROLE_GRANTS.member['responses.review']).toBe('own_shared')
    expect(DEFAULT_ROLE_GRANTS.member['responses.delete']).toBeUndefined()
    expect(withNeeds({ 'responses.export': 'own' })).toEqual({ 'responses.view': 'own', 'responses.export': 'own' })
    // A role saved as a list: responses reach as far as the forms did
    expect(grantsFromList(['forms.view', 'responses.view'])['responses.view']).toBe('own_shared')
    expect(grantsFromList(['forms.view', 'forms.all', 'responses.view'])['responses.view']).toBe('all')
  })
  it('leaves what every signed-in person needs open', () => {
    for (const path of ['/me/profile', '/navigation/counts', '/directory', '/settings/appearance', '/themes', '/option-lists/l1/options', '/notifications', '/folders'])
      expect(permissionFor('GET', path), path).toBeNull()
  })
  it('adds what an action needs, as far as it reaches', () => {
    expect(withNeeds({ 'forms.edit': 'own' })).toEqual({ 'forms.view': 'own', 'forms.edit': 'own' })
    expect(withNeeds({ 'forms.purge': 'shared' })).toEqual({ 'forms.view': 'shared', 'forms.delete': 'shared', 'forms.purge': 'shared' })
    // A scope an action doesn't offer is fitted; unknown actions and on / off actions are cleaned up
    expect(withNeeds({ 'folders.edit': 'shared', nonsense: 'all', 'forms.create': 'own' })).toEqual({ 'forms.create': 'all', 'folders.edit': 'own' })
    expect(DEFAULT_ROLE_GRANTS.owner).toEqual(ALL_GRANTS)
    expect(DEFAULT_ROLE_GRANTS.admin['roles.manage']).toBeUndefined()
    expect(DEFAULT_ROLE_GRANTS.member['forms.delete']).toBeUndefined()
  })
  it('treats own and shared as separate parts (None · Own · Shared · Own & shared · All)', () => {
    // Editing shared forms and viewing own ones: viewing must reach both
    expect(withNeeds({ 'forms.view': 'own', 'forms.edit': 'shared' })['forms.view']).toBe('own_shared')
    // Narrowing view to own takes edit off shared forms
    expect(setGrant({ 'forms.view': 'own_shared', 'forms.edit': 'shared' }, 'forms.view', 'own')['forms.edit']).toBeUndefined()
    expect(setGrant({ 'forms.view': 'all', 'forms.edit': 'own_shared' }, 'forms.view', 'shared')['forms.edit']).toBe('shared')
  })
  it('keeps a role consistent when one action changes', () => {
    const role = withNeeds({ 'forms.edit': 'all', 'forms.versions': 'all', 'forms.delete': 'all', 'forms.purge': 'all' })
    // Narrowing view narrows everything that needs it
    const narrowed = setGrant(role, 'forms.view', 'own')
    expect(narrowed['forms.edit']).toBe('own')
    expect(narrowed['forms.purge']).toBe('own')
    // Removing an action removes what needs it
    const noDelete = setGrant(role, 'forms.delete', null)
    expect(noDelete['forms.delete']).toBeUndefined()
    expect(noDelete['forms.purge']).toBeUndefined()
    expect(noDelete['forms.edit']).toBe('all')
    // Granting adds what it needs
    expect(setGrant({}, 'forms.duplicate', 'shared')).toEqual({ 'forms.view': 'shared', 'forms.create': 'all', 'forms.duplicate': 'shared' })
  })
  it('turns a role saved as a list into grants with the same reach', () => {
    const member = grantsFromList(['forms.view', 'forms.create', 'forms.edit', 'forms.publish', 'responses.view', 'responses.edit'])
    expect(member['forms.edit']).toBe('own_shared')
    expect(member['forms.publish']).toBe('own_shared')
    expect(member['forms.import']).toBe('all')
    expect(member['forms.delete']).toBeUndefined()
    expect(member['folders.create']).toBeUndefined()
    const admin = grantsFromList(['forms.view', 'forms.all', 'forms.delete', 'resources.manage', 'settings.manage'])
    expect(admin['forms.purge']).toBe('all')
    expect(admin['folders.delete']).toBe('all')
    expect(admin['folders.access']).toBe('all')
    expect(reachOf(ALL_GRANTS)).toBe(1)
    expect(ALL_PERMISSIONS.length).toBeGreaterThan(30)
  })
})

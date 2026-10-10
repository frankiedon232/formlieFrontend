import { describe, expect, it } from 'vitest'
import { levelOf } from '../../server/mock/data/formPermissions'
import type { StoredForm } from '../../server/mock/data/formStore'
import type { MockUser } from '../../server/mock/data/tenants'

// People access per form (decision 97).
const user = (id: string, role: MockUser['role'] = 'member') => ({ id, role }) as MockUser
const form = (extra: Partial<StoredForm> = {}) => ({ owner: { id: 'owner', name: 'Owner' }, ...extra }) as StoredForm

describe('people access', () => {
  it('workspace admins and the form owner always edit', () => {
    const locked = form({ team_access: 'none', grants: [{ user_id: 'boss', level: 'responses', granted_at: '' }] })
    expect(levelOf(locked, user('boss', 'admin'))).toBe('edit')
    expect(levelOf(locked, user('ceo', 'owner'))).toBe('edit')
    expect(levelOf(locked, user('owner'))).toBe('edit')
  })

  it('everyone else gets the workspace default (edit when not set)', () => {
    expect(levelOf(form(), user('a'))).toBe('edit')
    expect(levelOf(form({ team_access: 'view' }), user('a'))).toBe('view')
    expect(levelOf(form({ team_access: 'none' }), user('a'))).toBe('none')
  })

  it("a person's own level wins, more or less than the default", () => {
    const some = form({
      team_access: 'none',
      grants: [
        { user_id: 'more', level: 'edit', granted_at: '' },
        { user_id: 'less', level: 'responses', granted_at: '' },
      ],
    })
    expect(levelOf(some, user('more'))).toBe('edit')
    expect(levelOf(some, user('less'))).toBe('responses')
    expect(levelOf({ ...some, team_access: 'edit' }, user('less'))).toBe('responses')
  })
})

describe('seed users', () => {
  it('have unique ids per workspace', async () => {
    const { MOCK_USERS } = await import('../../server/mock/data/tenants')
    const keys = MOCK_USERS.map(person => `${person.tenant_id}:${person.id}`)
    expect(new Set(keys).size).toBe(keys.length)
    // The same id in two workspaces is one person (a member of both), same email.
    for (const person of MOCK_USERS) for (const other of MOCK_USERS) if (person.id === other.id) expect(other.email).toBe(person.email)
  })
})

describe('who may take an action on a form (F22 R2: role scope, maker, sharing)', () => {
  it('follows the role, its scope and the sharing', async () => {
    const { allows } = await import('../../server/mock/data/formPermissions')
    // Member: most actions on own and shared forms, never delete (not even their own)
    expect(allows(form(), user('owner'), 'delete')).toBe(false)
    expect(allows(form(), user('owner'), 'rename')).toBe(true)
    expect(allows(form({ team_access: 'edit' }), user('a'), 'rename')).toBe(true)
    // Shared for viewing only: may see and preview, not change
    expect(allows(form({ team_access: 'view' }), user('a'), 'preview')).toBe(true)
    expect(allows(form({ team_access: 'view' }), user('a'), 'rename')).toBe(false)
    // Admin: everything, everywhere
    expect(allows(form({ team_access: 'none' }), user('boss', 'admin'), 'purge')).toBe(true)
  })
  it('the app reads the answer the API sends (no answer means no)', async () => {
    const { canEditForm, formCan } = await import('../../shared/utils/forms/access')
    const can = { edit: true, publish: false } as never
    expect(canEditForm({ can })).toBe(true)
    expect(formCan({ can }, 'publish')).toBe(false)
    expect(canEditForm({})).toBe(false)
    expect(canEditForm(null)).toBe(false)
  })
})

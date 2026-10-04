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

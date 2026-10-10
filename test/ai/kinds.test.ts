import { describe, expect, it } from 'vitest'
import { AI_KINDS } from '../../shared/types/ai'
import { AI_KIND_META } from '../../shared/utils/ai/kinds'
import { DEFAULT_ROLE_GRANTS, permissionFor } from '../../shared/utils/auth/permissions'

describe('AI assistant', () => {
  it('maps its calls to the permission they need', () => {
    expect(permissionFor('GET', '/ai/settings')).toBe('ai.use')
    expect(permissionFor('PATCH', '/ai/settings')).toBe('ai.settings')
    expect(permissionFor('GET', '/ai/usage')).toBe('ai.use')
    expect(permissionFor('GET', '/ai/requests')).toBe('ai.history')
    expect(permissionFor('GET', '/ai/requests/insights')).toBe('ai.history')
    expect(permissionFor('DELETE', '/ai/requests/r1')).toBe('ai.history')
  })

  it('gives every kind an icon, a cost, a permission and a page', () => {
    for (const kind of AI_KINDS) {
      const meta = AI_KIND_META[kind]
      expect(meta.icon).toMatch(/^i-lucide-/)
      expect(meta.credits).toBeGreaterThan(0)
      expect(meta.permission).toMatch(/^ai\./)
      expect(meta.page).toMatch(/^\/ai/)
    }
  })
})

describe('AI assistant: who may do what', () => {
  it('maps every assistant call to its own permission', () => {
    expect(permissionFor('POST', '/ai/forms/draft')).toBe('ai.create')
    expect(permissionFor('POST', '/ai/templates/draft')).toBe('ai.create')
    expect(permissionFor('POST', '/ai/themes/draft')).toBe('ai.create')
    expect(permissionFor('POST', '/ai/forms/f1/assist')).toBe('ai.assist')
    expect(permissionFor('POST', '/ai/analysis')).toBe('ai.analyse')
    expect(permissionFor('POST', '/ai/digest')).toBe('ai.analyse')
    expect(permissionFor('POST', '/ai/ask')).toBe('ai.analyse')
    expect(permissionFor('POST', '/ai/responses/r1/summary')).toBe('ai.analyse')
    expect(permissionFor('POST', '/ai/forms/f1/translate')).toBe('ai.translate')
    expect(permissionFor('POST', '/ai/forms/f1/rewrite')).toBe('ai.translate')
    expect(permissionFor('POST', '/ai/requests/r1/apply')).toBe('ai.use')
    expect(permissionFor('POST', '/ai/requests/r1/discard')).toBe('ai.use')
  })

  it('lets members use the assistant but not manage it', () => {
    const member = DEFAULT_ROLE_GRANTS.member
    for (const permission of ['ai.use', 'ai.create', 'ai.assist', 'ai.analyse', 'ai.translate', 'ai.history'] as const) expect(member[permission]).toBeTruthy()
    expect(member['ai.settings']).toBeFalsy()
  })
})

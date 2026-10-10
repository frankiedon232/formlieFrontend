import { describe, expect, it } from 'vitest'
import { AI_KINDS } from '../../shared/types/ai'
import { AI_KIND_META } from '../../shared/utils/ai/kinds'
import { permissionFor } from '../../shared/utils/auth/permissions'

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

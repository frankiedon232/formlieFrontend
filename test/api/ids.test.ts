import { describe, expect, it } from 'vitest'
import { decodeId, decodeIds, decodeRouteParams, encodeId, encodeIds } from '../../server/mock/core/ids'

const ID = '81da3d63-5fe9-4ee4-9961-3159bda32354'

describe('encrypted references', () => {
  it('turns an id into a stable 27-character reference that reveals nothing', () => {
    const ref = encodeId(ID)
    expect(ref).toMatch(/^[A-Za-z0-9_-]{27}$/)
    expect(encodeId(ID)).toBe(ref) // bookmarks keep working
    expect(ref).not.toContain('81da3d63')
    expect(Buffer.from(ref, 'base64url').toString('hex')).not.toContain(ID.replace(/-/g, '').slice(0, 8))
    expect(decodeId(ref)).toBe(ID)
  })

  it('rejects typed-in and altered references', () => {
    const ref = encodeId(ID)
    const altered = (ref[0] === 'A' ? 'B' : 'A') + ref.slice(1)
    expect(decodeId(altered)).toBeNull()
    expect(decodeId('AAAAAAAAAAAAAAAAAAAAAAAAAAA')).toBeNull()
    expect(decodeId(ID)).toBeNull()
  })

  it('handles workspace template keys too', () => {
    const ref = encodeId('ws_3f9a0b1c2d4e')
    expect(ref).toMatch(/^[A-Za-z0-9_-]{27}$/)
    expect(decodeId(ref)).toBe('ws_3f9a0b1c2d4e')
  })

  it('encodes every id in a reply and decodes every reference in a request', () => {
    const reply = { id: ID, folder: { id: ID, name: 'Sales' }, url: `/api/v1/files/${ID}`, tags: ['plain'], count: 3, key: 'risk_assessment' }
    const out = encodeIds(reply)
    expect(JSON.stringify(out)).not.toContain(ID)
    expect(out.key).toBe('risk_assessment') // catalogue keys are names, not records
    expect(out.count).toBe(3)
    expect(decodeIds(out)).toEqual(reply)
  })

  it('never accepts a real id in the address', () => {
    const params: Record<string, string> = { id: ID }
    decodeRouteParams(params)
    expect(params.id).toBe('invalid-reference')
    const good: Record<string, string> = { id: encodeId(ID) }
    decodeRouteParams(good)
    expect(good.id).toBe(ID)
  })
})

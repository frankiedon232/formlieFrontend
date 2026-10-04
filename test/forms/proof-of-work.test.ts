import { describe, expect, it } from 'vitest'
import { checkWork, hasLeadingZeroBits, solveWork } from '../../shared/utils/forms/proof-of-work'

describe('proof of work (spam check)', () => {
  it('counts leading zero bits', () => {
    expect(hasLeadingZeroBits(new Uint8Array([0, 0x0f, 0xff]), 12)).toBe(true)
    expect(hasLeadingZeroBits(new Uint8Array([0, 0x0f, 0xff]), 13)).toBe(false)
    expect(hasLeadingZeroBits(new Uint8Array([0x80]), 1)).toBe(false)
    expect(hasLeadingZeroBits(new Uint8Array([0x7f]), 1)).toBe(true)
    expect(hasLeadingZeroBits(new Uint8Array([0xff]), 0)).toBe(true)
  })

  it('solves and checks a challenge', async () => {
    const nonce = await solveWork('test-salt', 10)
    expect(nonce).not.toBeNull()
    expect(await checkWork('test-salt', 10, nonce!)).toBe(true)
    expect(await checkWork('other-salt', 10, nonce!)).toBe(false)
    expect(await checkWork('test-salt', 10, -1)).toBe(false)
  })
})

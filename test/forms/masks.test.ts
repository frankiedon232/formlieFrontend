import { describe, expect, it } from 'vitest'
import { maskIp, maskIpv4, maskIpv6, maskMac } from '../../shared/utils/forms/masks'

describe('IP masks', () => {
  it('shapes IPv4 while typing', () => {
    expect(maskIpv4('192')).toBe('192')
    expect(maskIpv4('1920')).toBe('192.0')
    expect(maskIpv4('19202')).toBe('192.0.2')
    expect(maskIpv4('192.0.2.10')).toBe('192.0.2.10')
    expect(maskIpv4('256')).toBe('25.6')
    expect(maskIpv4('1.2.3.4.5')).toBe('1.2.3.45')
    expect(maskIpv4('10..0abc')).toBe('10.0')
    // Backspace-safe: no trailing dot is invented.
    expect(maskIpv4('192.')).toBe('192.')
    expect(maskIpv4('192')).toBe('192')
  })

  it('shapes IPv6 while typing', () => {
    expect(maskIpv6('2001DB8')).toBe('2001:db8')
    expect(maskIpv6('2001:db8::1')).toBe('2001:db8::1')
    expect(maskIpv6('2001:db8:::1')).toBe('2001:db8::1')
    expect(maskIpv6('::ffff:192.0.2.1')).toBe('::ffff:192.0.2.1')
    expect(maskIpv6('zz2001')).toBe('2001')
  })

  it('picks the version for "any"', () => {
    expect(maskIp('2001', 'any')).toBe('2001')
    expect(maskIp('20x01', 'any')).toBe('2001')
    expect(maskIp('19202', 'any')).toBe('192.0.2')
    expect(maskIp('192.02', 'any')).toBe('192.0.2')
    expect(maskIp('fe80::1', 'any')).toBe('fe80::1')
    expect(maskIp('2001db8', 'v4')).toBe('200.18')
  })
})

describe('MAC mask', () => {
  it('adds colons in capitals', () => {
    expect(maskMac('001a2b')).toBe('00:1A:2B')
    expect(maskMac('001a2b3c4d5e99')).toBe('00:1A:2B:3C:4D:5E')
    expect(maskMac('00:1a:2')).toBe('00:1A:2')
  })

  it('keeps dash and dot notations', () => {
    expect(maskMac('00-1a-2b-3c-4d-5e')).toBe('00-1A-2B-3C-4D-5E')
    expect(maskMac('001a.2b3c.4d5e')).toBe('001A.2B3C.4D5E')
  })
})

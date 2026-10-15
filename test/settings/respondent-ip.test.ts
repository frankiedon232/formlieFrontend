import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { maskIp, RESPONDENT_IP_MODES, respondentIp } from '../../shared/utils/privacy/ip'
import { privacySchema } from '../../shared/utils/settings/schemas'

describe('maskIp (owner 2026-10-15)', () => {
  it('ends IPv4 in 0', () => {
    expect(maskIp('203.0.113.45')).toBe('203.0.113.0')
    expect(maskIp('198.51.100.0')).toBe('198.51.100.0')
    expect(maskIp(' 192.0.2.255 ')).toBe('192.0.2.0')
  })
  it('keeps the first four IPv6 groups and zeroes the rest', () => {
    expect(maskIp('2001:db8:1:2:3:4:5:6')).toBe('2001:db8:1:2::')
    expect(maskIp('2001:0DB8:0001:0002:0003:0004:0005:0006')).toBe('2001:db8:1:2::')
    expect(maskIp('2001:db8::1')).toBe('2001:db8::')
    expect(maskIp('2001:db8:0:0:1:2:3:4')).toBe('2001:db8::')
    expect(maskIp('fe80::1%eth0')).toBe('fe80::')
    expect(maskIp('::1')).toBe('::')
  })
  it('treats IPv4 inside IPv6 by the IPv4 rule', () => {
    expect(maskIp('::ffff:203.0.113.45')).toBe('::ffff:203.0.113.0')
  })
  it('gives nothing for something that is not an address', () => {
    for (const value of ['unknown', '', '203.0.113', '256.1.1.1', '2001:db8:::1', '1:2:3:4:5:6:7:8:9', 'gggg::1']) expect(maskIp(value), value).toBeNull()
  })
})

describe('what a workspace sees under its setting', () => {
  it('has three choices, hidden first', () => {
    expect([...RESPONDENT_IP_MODES]).toEqual(['hidden', 'masked', 'full'])
  })
  it('shows nothing when hidden or unknown, partly or fully otherwise', () => {
    expect(respondentIp('203.0.113.45', 'hidden')).toBeNull()
    expect(respondentIp(null, 'full')).toBeNull()
    expect(respondentIp('203.0.113.45', 'masked')).toBe('203.0.113.0')
    expect(respondentIp('203.0.113.45', 'full')).toBe('203.0.113.45')
    expect(respondentIp('2001:db8:1:2:3:4:5:6', 'full')).toBe('2001:db8:1:2:3:4:5:6')
    expect(respondentIp('not an address', 'full')).toBeNull()
  })
  it('reads an older privacy setting as hidden', () => {
    const older = { retention_days: 0, notice_url: null, consent: false, consent_text: null }
    expect(privacySchema.parse(older).respondent_ip).toBe('hidden')
    expect(privacySchema.safeParse({ ...older, respondent_ip: 'masked' }).success).toBe(true)
    expect(privacySchema.safeParse({ ...older, respondent_ip: 'partly' }).success).toBe(false)
  })
})

describe('texts in all 20 languages', () => {
  const dir = join(__dirname, '../../i18n/locales')
  it('for Settings → Privacy and the response detail', () => {
    const files = readdirSync(dir).filter(file => file.endsWith('.json'))
    expect(files).toHaveLength(20)
    for (const file of files) {
      const j = JSON.parse(readFileSync(join(dir, file), 'utf8'))
      for (const key of ['title', 'hint', 'hidden', 'masked', 'full', 'hiddenExample']) expect(j.settings.privacy.ip[key], `${file} ${key}`).toBeTruthy()
      expect(j.settings.privacy.ip.example, file).toContain('{ip}')
      expect(j.responses.detail.ip, file).toBeTruthy()
    }
  })
})

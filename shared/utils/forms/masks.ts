/**
 * Typing masks for technical fields — they shape what is typed, the validator still decides
 * (`validate.ts`). Backspace-safe: a separator is only added when the next character arrives.
 *
 *   IPv4 → digits and dots, at most 3 digits / 255 per part, 4 parts (192.0.2.10)
 *   IPv6 → hex groups of up to 4 with colons, "::" once, an IPv4 tail allowed (2001:db8::1)
 *   MAC  → hex pairs joined by colons in capitals (00:1A:2B:3C:4D:5E); typing "-" or "." keeps
 *          the person's own format (00-1A-…, 001A.2B3C.4D5E) — only cleaned and capitalised
 */

export type IpVersion = 'any' | 'v4' | 'v6'

export function maskIpv4(raw: string): string {
  const parts: string[] = ['']
  for (const char of raw.replace(/[^\d.]/g, '')) {
    const current = parts.at(-1)!
    if (char === '.') {
      if (current && parts.length < 4) parts.push('')
      continue
    }
    // Overflow (4th digit or above 255) starts the next part.
    // A part never starts with 0 followed by more digits ("0" then "2" → 0.2).
    if (current.length === 3 || Number(current + char) > 255 || current === '0') {
      if (parts.length === 4) continue
      parts.push(char)
    } else parts[parts.length - 1] = current + char
  }
  return parts.join('.')
}

export function maskIpv6(raw: string): string {
  const cleaned = raw.toLowerCase().replace(/[^0-9a-f:.]/g, '')
  // IPv4 tail (::ffff:192.0.2.1): keep the dotted part as typed through the IPv4 mask.
  const lastColon = cleaned.lastIndexOf(':')
  const tail = cleaned.slice(lastColon + 1)
  if (tail.includes('.')) return `${maskIpv6Groups(cleaned.slice(0, lastColon + 1))}${maskIpv4(tail)}`
  return maskIpv6Groups(cleaned.replace(/\./g, ''))
}

function maskIpv6Groups(value: string): string {
  let out = ''
  let group = 0
  let groups = 1
  let doubled = false
  for (const char of value) {
    if (char === ':') {
      if (out.endsWith('::')) continue
      if (out.endsWith(':')) {
        if (doubled) continue
        doubled = true
      } else if (groups >= 8) continue
      out += ':'
      group = 0
      groups += out.endsWith('::') ? 0 : 1
      continue
    }
    if (group === 4) {
      if (groups >= 8) continue
      out += ':'
      groups += 1
      group = 0
    }
    out += char
    group += 1
  }
  return out
}

/**
 * "any": IPv6 as soon as a colon or a hex letter appears, IPv4 once a dot is typed; plain digits
 * stay as typed until then ("2001" may become either).
 */
export function maskIp(raw: string, version: IpVersion = 'any'): string {
  if (version === 'v4') return maskIpv4(raw)
  if (version === 'v6') return maskIpv6(raw)
  if (/[:a-f]/i.test(raw)) return maskIpv6(raw)
  const digits = raw.replace(/\D/g, '')
  // More than 4 digits in a row can only be IPv4 (an IPv6 group holds at most 4).
  return raw.includes('.') || digits.length > 4 ? maskIpv4(raw) : digits
}

export function maskMac(raw: string): string {
  const upper = raw.toUpperCase()
  // The person chose another notation: keep it, only clean it.
  if (/[-.]/.test(upper)) return upper.replace(/[^0-9A-F.-]/g, '').slice(0, 17)
  const hex = upper.replace(/[^0-9A-F]/g, '').slice(0, 12)
  return hex.match(/.{1,2}/g)?.join(':') ?? ''
}

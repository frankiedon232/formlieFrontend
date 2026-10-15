/**
 * Respondent IP addresses (owner 2026-10-15): each workspace decides what its people see (Settings → Privacy,
 * `respondent_ip`); Formalie keeps the full address for security either way. The backend ports these rules (parity).
 *   hidden  → nothing (the default, as before)
 *   masked  → partly hidden: IPv4 ends in 0 (203.0.113.45 → 203.0.113.0); IPv6 keeps its first four groups
 *             (2001:db8:1:2:3:4:5:6 → 2001:db8:1:2::)
 *   full    → the address as recorded
 */
export const RESPONDENT_IP_MODES = ['hidden', 'masked', 'full'] as const
export type RespondentIpMode = (typeof RESPONDENT_IP_MODES)[number]

const IPV4 = /^(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/

/** Eight IPv6 groups as numbers, or null when it isn't an IPv6 address (no IPv4 tail). */
function ipv6Groups(value: string): number[] | null {
  if (!/^[0-9a-f:]+$/i.test(value) || value.split('::').length > 2) return null
  const [head = '', tail] = value.split('::')
  const part = (text: string) => (text ? text.split(':') : [])
  const left = part(head)
  const right = tail === undefined ? [] : part(tail)
  const missing = 8 - left.length - right.length
  if (tail === undefined ? left.length !== 8 : missing < 1) return null
  const all = [...left, ...Array(tail === undefined ? 0 : missing).fill('0'), ...right]
  if (all.some(group => !/^[0-9a-f]{1,4}$/i.test(group))) return null
  return all.map(group => parseInt(group, 16))
}

/** RFC 5952 text: lowercase, no leading zeros, the longest run of two or more zero groups written as ::. */
function ipv6Text(groups: number[]): string {
  let best = -1
  let bestLength = 1
  for (let i = 0; i < 8; ) {
    if (groups[i] !== 0) {
      i++
      continue
    }
    let j = i
    while (j < 8 && groups[j] === 0) j++
    if (j - i > bestLength) {
      best = i
      bestLength = j - i
    }
    i = j
  }
  const hex = groups.map(group => group.toString(16))
  if (best < 0) return hex.join(':')
  return `${hex.slice(0, best).join(':')}::${hex.slice(best + bestLength).join(':')}`
}

/** The address partly hidden; null when it isn't a valid IPv4 or IPv6 address. */
export function maskIp(ip: string): string | null {
  const value = ip.trim()
  if (IPV4.test(value)) return value.replace(/\.\d+$/, '.0')
  // IPv4 inside IPv6 (::ffff:203.0.113.45): the IPv4 rule
  const mapped = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/i.exec(value)
  if (mapped && IPV4.test(mapped[1]!)) return `::ffff:${mapped[1]!.replace(/\.\d+$/, '.0')}`
  const groups = ipv6Groups(value.split('%')[0]!)
  if (!groups) return null
  return ipv6Text([...groups.slice(0, 4), 0, 0, 0, 0])
}

/** What a workspace's people see of a respondent's address under its setting (null = nothing). */
export function respondentIp(ip: string | null | undefined, mode: RespondentIpMode): string | null {
  if (!ip || mode === 'hidden') return null
  if (mode === 'masked') return maskIp(ip)
  const value = ip.trim()
  return IPV4.test(value) || ipv6Groups(value.split('%')[0]!) || /^::ffff:\d+\.\d+\.\d+\.\d+$/i.test(value) ? value : null
}

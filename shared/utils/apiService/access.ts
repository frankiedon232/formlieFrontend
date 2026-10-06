/**
 * Access rules shared by the portal and the server (F13 M3, SECURITY-PROTOCOL §9): checking a
 * rule's values (IP addresses and ranges, domains, countries, regions), matching a caller, and the
 * decision: a matching block refuses; when allow rules apply, the caller must match one of them.
 * Domain rules use the browser's Origin (or Referer), so they only ever match browser callers.
 */
import type { ApiAccessRule, ApiRuleKind } from '#shared/types/apiService'
import { isCountryCode } from '#shared/utils/platform/countries'

export interface AccessCaller {
  ip: string
  /** Host of the Origin / Referer header (browser callers), lower case. */
  domain: string | null
  /** ISO country of the IP address (GeoIP on the server). */
  country: string | null
}
export interface AccessDecision {
  allowed: boolean
  /** blocked = a block rule matched; not_allowed = allow rules apply and none matched. */
  reason: 'blocked' | 'not_allowed' | null
  rule: { id: string; action: 'allow' | 'block'; value: string } | null
}

/** Problems with one value of a rule: `required`, `ip`, `domain`, `country` or `region`. */
export function checkRuleValue(kind: ApiRuleKind, value: string): string | null {
  const text = value.trim()
  if (!text) return 'required'
  if (kind === 'ip') return parseCidr(text) ? null : 'ip'
  if (kind === 'domain') return DOMAIN_PATTERN.test(text.toLowerCase()) ? null : 'domain'
  if (kind === 'country') return isCountryCode(text.toUpperCase()) ? null : 'country'
  return text.toUpperCase() in REGIONS ? null : 'region'
}

/** A value as stored: IPs as typed, domains in lower case, countries and regions in upper case. */
export function normaliseRuleValue(kind: ApiRuleKind, value: string) {
  const text = value.trim()
  return kind === 'domain' ? text.toLowerCase() : kind === 'country' || kind === 'region' ? text.toUpperCase() : text
}

/** The region (continent) a country is in, or null. */
export function regionOf(country: string | null): string | null {
  if (!country) return null
  const code = country.toUpperCase()
  return Object.keys(REGIONS).find(region => REGIONS[region]!.includes(code)) ?? null
}

/** Whether a caller matches one value of a rule. */
export function matchesValue(kind: ApiRuleKind, value: string, caller: AccessCaller): boolean {
  if (kind === 'ip') return ipInCidr(caller.ip, value)
  if (kind === 'domain') {
    if (!caller.domain) return false
    const domain = caller.domain.toLowerCase()
    return value.startsWith('*.') ? domain.endsWith(value.slice(1)) && domain !== value.slice(2) : domain === value
  }
  if (kind === 'country') return !!caller.country && caller.country.toUpperCase() === value
  return regionOf(caller.country) === value
}

/** The decision for a caller against the rules that apply to an endpoint (enabled ones only). */
export function decideAccess(rules: Pick<ApiAccessRule, 'id' | 'action' | 'kind' | 'values' | 'enabled'>[], caller: AccessCaller): AccessDecision {
  const active = rules.filter(rule => rule.enabled)
  for (const rule of active.filter(item => item.action === 'block')) {
    const value = rule.values.find(item => matchesValue(rule.kind, item, caller))
    if (value) return { allowed: false, reason: 'blocked', rule: { id: rule.id, action: 'block', value } }
  }
  const allows = active.filter(rule => rule.action === 'allow')
  if (!allows.length) return { allowed: true, reason: null, rule: null }
  for (const rule of allows) {
    const value = rule.values.find(item => matchesValue(rule.kind, item, caller))
    if (value) return { allowed: true, reason: null, rule: { id: rule.id, action: 'allow', value } }
  }
  return { allowed: false, reason: 'not_allowed', rule: null }
}

/** The rules that apply to an endpoint: everywhere, its service, itself. */
export const rulesFor = <T extends { scope: { type: string; id: string | null } }>(rules: T[], endpoint: { id: string; service_id: string }) =>
  rules.filter(rule => rule.scope.type === 'all' || (rule.scope.type === 'service' && rule.scope.id === endpoint.service_id) || (rule.scope.type === 'endpoint' && rule.scope.id === endpoint.id))

// ── IP addresses ─────────────────────────────────────────────────────────────────────────

/** An IP address as a number and its family. */
export function parseIp(text: string): { family: 4 | 6; value: bigint } | null {
  const v4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(text)
  if (v4) {
    const parts = v4.slice(1).map(Number)
    if (parts.some(part => part > 255)) return null
    return { family: 4, value: parts.reduce((sum, part) => (sum << 8n) + BigInt(part), 0n) }
  }
  const mapped = /^::ffff:(\d{1,3}(?:\.\d{1,3}){3})$/i.exec(text)
  if (mapped) return parseIp(mapped[1]!)
  if (!/^[0-9a-f:]+$/i.test(text) || !text.includes(':') || (text.match(/::/g) ?? []).length > 1) return null
  const [head = '', tail = ''] = text.split('::')
  const left = head ? head.split(':') : []
  const right = text.includes('::') ? (tail ? tail.split(':') : []) : []
  const groups = text.includes('::') ? [...left, ...Array(8 - left.length - right.length).fill('0'), ...right] : left
  if (groups.length !== 8 || groups.some(group => !/^[0-9a-f]{1,4}$/i.test(group))) return null
  return { family: 6, value: groups.reduce((sum, group) => (sum << 16n) + BigInt(parseInt(group, 16)), 0n) }
}

/** An address or a range (`203.0.113.0/24`, `2001:db8::/32`). */
export function parseCidr(text: string): { family: 4 | 6; value: bigint; bits: number } | null {
  const [address = '', prefix] = text.trim().split('/')
  const ip = parseIp(address)
  if (!ip) return null
  const max = ip.family === 4 ? 32 : 128
  const bits = prefix === undefined ? max : /^\d{1,3}$/.test(prefix) ? Number(prefix) : -1
  if (bits < 0 || bits > max) return null
  return { ...ip, bits }
}

export function ipInCidr(ip: string, cidr: string): boolean {
  const caller = parseIp(ip)
  const range = parseCidr(cidr)
  if (!caller || !range || caller.family !== range.family) return false
  const shift = BigInt((range.family === 4 ? 32 : 128) - range.bits)
  return caller.value >> shift === range.value >> shift
}

const DOMAIN_PATTERN = /^(\*\.)?(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/
/** Regions by continent (UN geoscheme; the Americas split North / Central / Caribbean and South). */
export const REGIONS: Record<string, string[]> = {
  AF: 'DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU YT MA MZ NA NE NG RE RW SH ST SN SC SL SO ZA SS SD TZ TG TN UG EH ZM ZW IO'.split(' '),
  AS: 'AF AM AZ BH BD BT BN KH CN CY GE HK IN ID IR IQ IL JP JO KZ KW KG LA LB MO MY MV MN MM NP KP OM PK PS PH QA SA SG KR LK SY TW TJ TH TL TR TM AE UZ VN YE CC CX'.split(' '),
  EU: 'AX AL AD AT BY BE BA BG HR CZ DK EE FO FI FR DE GI GR GG VA HU IS IE IM IT JE XK LV LI LT LU MT MD MC ME NL MK NO PL PT RO RU SM RS SK SI ES SE CH UA GB'.split(' '),
  NA: 'AG AI AW BS BB BZ BM BQ VG CA KY CR CU CW DM DO SV GL GD GP GT HT HN JM MQ MX MS NI PA PR BL KN LC MF PM VC SX TT TC US VI'.split(' '),
  OC: 'AS AU CK FJ PF GU KI MH FM NR NC NZ NU NF MP PW PG PN WS SB TK TO TV VU WF'.split(' '),
  SA: 'AR BO BR CL CO EC FK GF GY PY PE SR UY VE'.split(' '),
}
/** Rate limit choices (calls per minute; null = no limit). */
export const RATE_LIMIT_CHOICES: (number | null)[] = [30, 60, 120, 300, 600, 1200, 3000, null]

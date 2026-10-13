/**
 * DEVELOPMENT ONLY. Per-address daily caps across every workspace (security review L19, 2026-10-13), as the backend
 * has them: whoever fills in a form chooses where its copy and its verification codes go, so one address gets at
 * most 5 copies of answers and 10 verification codes a day from all of Formalie. In memory: a restart starts over.
 */
const DAY_MS = 86_400_000
export const RECEIPTS_PER_ADDRESS_PER_DAY = 5
export const CODES_PER_ADDRESS_PER_DAY = 10

const sent = new Map<string, number[]>()

/** True (and counted) when one more may go to this address today; false when the cap is reached. */
export function underDailyCap(bucket: string, address: string, limit: number, now = Date.now()): boolean {
  const key = `${bucket}|${address.trim().toLowerCase()}`
  const recent = (sent.get(key) ?? []).filter(at => at > now - DAY_MS)
  if (recent.length >= limit) {
    sent.set(key, recent)
    return false
  }
  sent.set(key, [...recent, now])
  return true
}

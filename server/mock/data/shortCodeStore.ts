/**
 * Retired short link codes (F10 M3, owner question 2026-10-04: "no conflict"): a code that was
 * removed is never handed out again — an old poster or QR code must never open another form, let
 * alone another organisation's. Kept even when the form itself is deleted for good.
 * The real backend keeps them in a table with a unique constraint on the code.
 */
import { loadPersisted, savePersisted } from '../core/persist'

const retired = new Set<string>(loadPersisted<string[]>('short-codes-retired', []))

export const isRetiredShortCode = (code: string) => retired.has(code)

export function retireShortCode(code: string) {
  retired.add(code)
  savePersisted('short-codes-retired', () => [...retired])
}

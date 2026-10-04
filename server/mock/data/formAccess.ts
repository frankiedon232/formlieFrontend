/**
 * Who may open a form (F10 M3, decisions 92 and 96) — one unlock mechanism for every access mode:
 *   public        — everyone
 *   password      — after the right password
 *   invite        — with a personal invitation link (one person, one response)
 *   organisation  — signed-in members of the workspace (a short sign-in pass from the portal)
 * The browser keeps an HttpOnly cookie per form: `{until}.{who}.{signature}`, signed with the form's
 * access version — changing the mode or the password, or revoking an invitation, locks people out.
 */
import { createHash, createHmac, randomBytes, timingSafeEqual } from 'node:crypto'
import type { H3Event } from 'h3'
import type { StoredForm } from './formStore'
import { MOCK_USERS, type MockTenant, type MockUser } from './tenants'

const SECRET = randomBytes(32)
export const UNLOCK_TTL_MS = 12 * 3_600_000
const PASS_TTL_MS = 2 * 60_000

export type FormAccessMode = 'public' | 'password' | 'invite' | 'organisation'
export const accessOf = (form: StoredForm): FormAccessMode => form.access ?? 'public'

export interface FormInvite {
  id: string
  email: string
  name: string | null
  /** SHA-256 of the personal token — the token itself is only in the invitation link. */
  token_hash: string
  created_at: string
  sent_at: string
  opened_at: string | null
  responded_at: string | null
  revoked_at: string | null
}

/** Who opened the form: the visitor's identity behind the unlock cookie. */
export type Visitor = { kind: 'public' } | { kind: 'password' } | { kind: 'invite'; invite: FormInvite } | { kind: 'member'; user: MockUser }

const sign = (value: string) => createHmac('sha256', SECRET).update(value).digest('base64url')
const sameText = (a: string, b: string) => {
  const left = Buffer.from(a)
  const right = Buffer.from(b)
  return left.length === right.length && timingSafeEqual(left, right)
}
const accessVersion = (form: StoredForm) => `${accessOf(form)}:${form.password?.version ?? 0}`
export const unlockCookieName = (form: StoredForm) => `formalie_unlock_${form.public_key}`

/** The cookie value for a visitor (`who` = pw | inv~{id} | usr~{id}). */
export function unlockValue(form: StoredForm, who: string): { value: string; maxAge: number } {
  const until = Date.now() + UNLOCK_TTL_MS
  return { value: `${until}.${who}.${sign(`${form.id}|${accessVersion(form)}|${who}|${until}`)}`, maxAge: UNLOCK_TTL_MS / 1000 }
}

/** The visitor behind this browser's cookie — or null when the form is locked for them. */
export function visitorOf(event: H3Event, form: StoredForm, tenant: MockTenant): Visitor | null {
  const mode = accessOf(form)
  if (mode === 'public') return { kind: 'public' }
  const [until, who, signature] = (getCookie(event, unlockCookieName(form)) ?? '').split('.')
  if (!until || !who || !signature || Number(until) < Date.now()) return null
  if (!sameText(signature, sign(`${form.id}|${accessVersion(form)}|${who}|${until}`))) return null
  const [kind, id] = who.split('~')
  if (mode === 'password' && kind === 'pw') return { kind: 'password' }
  if (mode === 'invite' && kind === 'inv') {
    const invite = (form.invites ?? []).find(item => item.id === id && !item.revoked_at)
    return invite ? { kind: 'invite', invite } : null
  }
  if (mode === 'organisation' && kind === 'usr') {
    const user = MOCK_USERS.find(item => item.id === id && item.tenant_id === tenant.id && !item.disabled)
    return user ? { kind: 'member', user } : null
  }
  return null
}

// ── Invitations ─────────────────────────────────────────────────────────────────────────
export const hashToken = (token: string) => createHash('sha256').update(token).digest('base64url')
export const newInviteToken = () => randomBytes(24).toString('base64url')
export const inviteByToken = (form: StoredForm, token: string) => {
  const hash = hashToken(token)
  return (form.invites ?? []).find(item => !item.revoked_at && sameText(item.token_hash, hash)) ?? null
}

// ── Sign-in passes (organisation-only) ──────────────────────────────────────────────────
// The portal (where the member is signed in) hands out a 2-minute pass for one form; the public
// page trades it for the unlock cookie on its own host (works on forms.* too).
export function issuePass(form: StoredForm, user: MockUser): string {
  const until = Date.now() + PASS_TTL_MS
  return `${until}.${user.id}.${sign(`pass|${form.id}|${user.id}|${until}`)}`
}
export function readPass(form: StoredForm, tenant: MockTenant, pass: string): MockUser | null {
  const [until, userId, signature] = pass.split('.')
  if (!until || !userId || !signature || Number(until) < Date.now()) return null
  if (!sameText(signature, sign(`pass|${form.id}|${userId}|${until}`))) return null
  return MOCK_USERS.find(item => item.id === userId && item.tenant_id === tenant.id && !item.disabled) ?? null
}

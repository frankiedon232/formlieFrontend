/**
 * Confirming the password before something sensitive (F13 M7: viewing a token, API key or webhook
 * secret again). Five wrong tries in 15 minutes lock it for that person (`FRM-AUTH-1004`); a wrong
 * one answers `FRM-AUTH-1013` with the tries left. 422, not 401, so the portal does not take it for
 * an expired session. The backend asks again through the person's own sign-in method (password,
 * or the single sign-on provider for people without one).
 */
import { passwordMatches, type MockUser } from '../data/tenants'
import { MockError } from './respond'

const WINDOW_MS = 15 * 60_000
const MAX_TRIES = 5
const failures = new Map<string, number[]>()

export function confirmPassword(user: MockUser, password: unknown) {
  const now = Date.now()
  const recent = (failures.get(user.id) ?? []).filter(at => at > now - WINDOW_MS)
  if (recent.length >= MAX_TRIES) throw new MockError('FRM-AUTH-1004')
  if (typeof password !== 'string' || !password || !passwordMatches(user, password)) {
    recent.push(now)
    failures.set(user.id, recent)
    throw new MockError('FRM-AUTH-1013', [{ field: 'password', message: String(Math.max(0, MAX_TRIES - recent.length)) }])
  }
  failures.delete(user.id)
}

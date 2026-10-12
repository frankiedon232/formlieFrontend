/**
 * Sign-in providers' logos and brand names (names are not translated), shared by the sign-in buttons and the sign-in
 * page preview. Sign-up and every sign-in page offer exactly these (owner, 2026-10-12); a workspace adds single sign-on.
 */
import type { AuthProvider } from '#shared/types/auth'

export type SocialProvider = Exclude<AuthProvider, 'password'>

export const PROVIDER_ICONS: Record<AuthProvider, string> = {
  password: 'i-lucide-key-round',
  google: 'i-simple-icons-google',
  facebook: 'i-simple-icons-facebook',
}

export const PROVIDER_NAMES: Record<SocialProvider, string> = {
  google: 'Google',
  facebook: 'Facebook',
}

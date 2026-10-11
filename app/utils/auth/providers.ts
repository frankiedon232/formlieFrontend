/**
 * Sign-in providers' logos and brand names (names are not translated), shared by the sign-in buttons,
 * Settings → Sign-in and the sign-in page preview.
 */
import type { AuthProvider } from '#shared/types/auth'

export type SocialProvider = Exclude<AuthProvider, 'password'>

export const PROVIDER_ICONS: Record<AuthProvider, string> = {
  password: 'i-lucide-key-round',
  google: 'i-simple-icons-google',
  microsoft: 'i-simple-icons-microsoft',
  facebook: 'i-simple-icons-facebook',
}

export const PROVIDER_NAMES: Record<SocialProvider, string> = {
  google: 'Google',
  microsoft: 'Microsoft',
  facebook: 'Facebook',
}

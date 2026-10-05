/**
 * Platform-wide settings for the mock (managed by the super admin, F23): today the legal pages
 * linked from every public form. Defaults come from runtimeConfig.public.legal; a stored value
 * wins, so a change applies to every form at once without a redeploy. Persisted across reloads.
 */
import type { H3Event } from 'h3'
import { loadPersisted, savePersisted } from '../core/persist'

interface PlatformSettings {
  legal?: { terms_url?: string; privacy_url?: string }
  /** Addresses Formalie connects to customer databases from (F12; documentation range in the mock). */
  egress_ips?: string[]
}

const settings = loadPersisted<PlatformSettings>('platform', {})

export function platformLegal(event: H3Event) {
  const fallback = useRuntimeConfig(event).public.legal
  return {
    terms_url: settings.legal?.terms_url || fallback.termsUrl,
    privacy_url: settings.legal?.privacy_url || fallback.privacyUrl,
  }
}

export function setPlatformLegal(legal: { terms_url?: string; privacy_url?: string }) {
  settings.legal = { ...settings.legal, ...legal }
  savePersisted('platform', () => settings)
}

/** Formalie's outgoing addresses, shown on Data sources so customers can allow them (F23 edits them). */
export const platformEgressIps = () => settings.egress_ips ?? ['203.0.113.10', '203.0.113.11', '2001:db8:4f::10']

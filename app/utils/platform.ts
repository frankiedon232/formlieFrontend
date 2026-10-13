/**
 * Platform settings (docs/API-HOOKS.md): the shape of GET {API}/public/platform (contact addresses, status page,
 * social profiles, legal entity), checked before use, and the defaults used when the API doesn't answer. Pure, so
 * it is unit-tested.
 */
import { z } from 'zod'

export const SOCIAL_NETWORKS = ['linkedin', 'x', 'youtube', 'github'] as const
export type SocialNetwork = (typeof SOCIAL_NETWORKS)[number]

/** Names and icons as the networks write them (brand names, not translated). */
export const SOCIAL_META: Record<SocialNetwork, { name: string; icon: string }> = {
  linkedin: { name: 'LinkedIn', icon: 'i-simple-icons-linkedin' },
  x: { name: 'X', icon: 'i-simple-icons-x' },
  youtube: { name: 'YouTube', icon: 'i-simple-icons-youtube' },
  github: { name: 'GitHub', icon: 'i-simple-icons-github' },
}

export interface Platform {
  supportEmail: string
  salesEmail: string
  /** Null when the owner clears it in the platform admin: the place that shows it is then hidden. */
  privacyEmail: string | null
  securityEmail: string | null
  abuseEmail: string | null
  statusUrl: string | null
  social: { network: SocialNetwork; url: string }[]
  legalEntity: { name: string | null; address: string | null }
}

export const FALLBACK_PLATFORM: Platform = {
  supportEmail: 'support@formalie.com',
  salesEmail: 'sales@formalie.com',
  privacyEmail: 'privacy@formalie.com',
  securityEmail: 'security@formalie.com',
  abuseEmail: 'abuse@formalie.com',
  statusUrl: null,
  social: [],
  legalEntity: { name: 'UNET SYSTEM TECH LTD', address: null },
}

const httpsUrl = z
  .string()
  .url()
  .refine(url => url.startsWith('https://'))
const email = z.string().email()
// Each field falls back on its own, so one bad value never drops the rest.
const schema = z.object({
  data: z.object({
    support_email: email.catch(FALLBACK_PLATFORM.supportEmail),
    sales_email: email.catch(FALLBACK_PLATFORM.salesEmail),
    // Missing (an older backend) keeps the default; null hides it; a bad value keeps the default.
    privacy_email: email
      .nullable()
      .default(FALLBACK_PLATFORM.privacyEmail)
      .catch(FALLBACK_PLATFORM.privacyEmail),
    security_email: email
      .nullable()
      .default(FALLBACK_PLATFORM.securityEmail)
      .catch(FALLBACK_PLATFORM.securityEmail),
    abuse_email: email.nullable().default(FALLBACK_PLATFORM.abuseEmail).catch(FALLBACK_PLATFORM.abuseEmail),
    status_url: httpsUrl.nullable().catch(null),
    social: z.record(z.string(), z.unknown()).catch({}),
    legal_entity: z
      .object({
        name: z.string().trim().min(1).nullable().catch(null),
        address: z.string().trim().min(1).nullable().catch(null),
      })
      .catch(FALLBACK_PLATFORM.legalEntity),
  }),
})

/** The platform settings from the API answer, or null when it isn't one. Only known networks with https links. */
export function parsePlatform(answer: unknown): Platform | null {
  const result = schema.safeParse(answer)
  if (!result.success) return null
  const data = result.data.data
  return {
    supportEmail: data.support_email,
    salesEmail: data.sales_email,
    privacyEmail: data.privacy_email,
    securityEmail: data.security_email,
    abuseEmail: data.abuse_email,
    statusUrl: data.status_url,
    social: SOCIAL_NETWORKS.flatMap(network => {
      const url = httpsUrl.safeParse(data.social[network])
      return url.success ? [{ network, url: url.data }] : []
    }),
    legalEntity: data.legal_entity,
  }
}

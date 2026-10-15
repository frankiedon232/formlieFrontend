/**
 * DEVELOPMENT ONLY. What PUT /settings/sso accepts in the mock (docs/API-CONTRACT.md → Settings), kept apart from the
 * route so tests can run it. The provider is one of the three choices (owner 2026-10-15: Microsoft Entra ID, Google
 * Workspace, SAML 2.0); anything else fails like any invalid value (parseBody → 422 FRM-GEN-1002).
 */
import { z } from 'zod'
import { SSO_PROVIDERS } from '#shared/types/sso'
import { isEmailDomain } from '#shared/utils/settings/schemas'

const url = z
  .string()
  .trim()
  .max(500)
  .nullable()
  .transform(value => value || null)
  .refine(value => !value || /^https:\/\/[^\s]+$/i.test(value), 'https')
const text = (max: number) =>
  z
    .string()
    .trim()
    .max(max)
    .nullable()
    .transform(value => value || null)
export const ssoSaveSchema = z.object({
  provider: z.enum(SSO_PROVIDERS),
  label: z.string().trim().min(1).max(40),
  saml: z.object({ metadata_url: url, entity_id: text(500), sso_url: url, certificate: text(10_000) }).partial().optional(),
  oidc: z.object({ issuer: url, client_id: text(300), client_secret: z.string().max(1000).nullable().optional() }).optional(),
  domains: z.array(z.string().trim().toLowerCase().transform(value => value.replace(/^@/, '')).refine(isEmailDomain, 'domain')).max(20),
  enforce: z.boolean(),
  auto_create: z.boolean(),
  default_role: z.string().min(1).max(100),
})

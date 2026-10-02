/**
 * Client-side validation for the auth forms (CLAUDE.md rule 11). Same rules as the server;
 * messages translated. Usage: `const schema = computed(() => loginSchema(t))`.
 */
import { z } from 'zod'

type T = (key: string, params?: Record<string, unknown>) => string

const email = (t: T) => z.email(t('auth.validation.email'))

const strongPassword = (t: T) =>
  z
    .string()
    .min(PASSWORD_MIN_LENGTH, t('auth.validation.passwordPolicy', { min: PASSWORD_MIN_LENGTH }))
    .refine(meetsPasswordPolicy, t('auth.validation.passwordPolicy', { min: PASSWORD_MIN_LENGTH }))

export const loginSchema = (t: T) =>
  z.object({ email: email(t), password: z.string().min(1, t('auth.validation.password')) })

export const emailOnlySchema = (t: T) => z.object({ email: email(t) })

export const signupAccountSchema = (t: T) =>
  z.object({
    first_name: z.string().trim().min(1, t('auth.validation.required')).max(60),
    last_name: z.string().trim().min(1, t('auth.validation.required')).max(60),
    email: email(t),
    password: strongPassword(t),
  })

export const workspaceSchema = (t: T) =>
  z.object({
    company_name: z.string().trim().min(2, t('auth.validation.companyName')).max(80),
    subdomain: z
      .string()
      .trim()
      .toLowerCase()
      .min(3, t('auth.validation.subdomain'))
      .refine(isValidSubdomain, t('auth.validation.subdomain')),
  })

export const resetSchema = (t: T) =>
  z
    .object({ password: strongPassword(t), confirm: z.string() })
    .refine(value => value.password === value.confirm, {
      message: t('auth.validation.passwordMatch'),
      path: ['confirm'],
    })

/** "Remedy Legal Ltd." → "remedylegal" (suggestion for the subdomain field). */
export const suggestSubdomain = (company: string) =>
  company
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '')
    .slice(0, 30)

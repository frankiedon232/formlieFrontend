/** Public form pages (F10) — docs/API-CONTRACT.md → Public. No sign-in; the workspace comes from the host or the form key. */
import type { FormSchemaV1 } from '../utils/forms/schema'

/**
 * What a visitor can do with the form right now:
 * open · closed (closed or archived by the workspace) · not_published (never published yet).
 * Later (Share settings, M3): expired · limit_reached · scheduled · password.
 */
export type PublicFormState = 'open' | 'closed' | 'not_published' | 'expired' | 'scheduled'

export interface PublicWorkspace {
  name: string
  logo_url: string | null
  primary: string | null
  /** Own subdomain, or null for workspaces served from forms.formalie.com. */
  subdomain: string | null
  /** The organisation's own website (https), or null. */
  website: string | null
}

export interface PublicFormSeo {
  title: string
  description: string
  /** Absolute https URL for link cards, or null. */
  image: string | null
  /** Ask search engines not to list the form. */
  noindex: boolean
}

export interface PublicForm {
  key: string
  name: string
  state: PublicFormState
  /** Availability: open from / until (state expired / scheduled follows from them). */
  opens_at: string | null
  closes_at: string | null
  /** The published form (theme resolved) — only when `state` is `open`. */
  schema: FormSchemaV1 | null
  workspace: PublicWorkspace
  seo: PublicFormSeo
  /** Formalie's legal pages for the footer — platform settings (super admin, F23), config as fallback. */
  legal: { terms_url: string; privacy_url: string }
  /** Languages the form offers (its main language first) and the one served. */
  languages: string[]
  language: string
}

/** POST /public/forms/{key}/submit → the response and what to show next. */
export interface PublicSubmitResult {
  response_id: string
  /** True when this fill-in session was already submitted (same Idempotency-Key): nothing new was stored. */
  duplicate: boolean
  thank_you: { title: string; message: string; redirect_url: string | null }
}

/** What the renderer's `submit` handler reports back (public page, F10). */
export type RendererSubmitOutcome =
  | { done: true; thank_you?: PublicSubmitResult['thank_you'] }
  | {
      done: false
      issues?: { key: string; code: string; params?: Record<string, unknown> }[]
      /**
       * already — this browser already sent one (offer "for someone else") · duplicate — the exact same
       * answers were already sent · registered — this person (their email / ID) already responded ·
       * possible — looks like an earlier response: ask "different person?" · verify — confirm the email first.
       */
      reason?: 'already' | 'duplicate' | 'registered' | 'possible' | 'verify'
      /** The identity question concerned, and a masked hint of the earlier response (never its details). */
      field?: string
      hint?: { at?: string; email?: string }
    }

/** What the public page lets the renderer do for the respondent (F10). */
export interface RendererRespondent {
  /** This browser already sent the form. */
  alreadySent: boolean
  /** Start a new response for someone else. */
  another: () => void
  /** "Yes, I'm a different person" (a similar earlier response exists). */
  confirmDifferent: () => void
  /** Email code step (forms that verify the respondent's email). */
  sendCode: (email: string) => Promise<{ sentTo: string; devCode: string | null } | null>
  confirmCode: (email: string, code: string) => Promise<boolean>
}

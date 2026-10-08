/** Public form pages (F10), docs/API-CONTRACT.md → Public. No sign-in; the workspace comes from the host or the form key. */
import type { FormSchemaV1 } from '../utils/forms/schema'

/**
 * What a visitor can do with the form right now:
 * open · closed (closed or archived by the workspace) · not_published (never published yet) ·
 * expired / scheduled (availability dates) · limit_reached (response limit, Share settings).
 * A password form is `open` with `locked` until the visitor enters the password.
 */
export type PublicFormState = 'open' | 'closed' | 'not_published' | 'expired' | 'scheduled' | 'limit_reached'

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
  /** The published form (theme resolved), only when `state` is `open`. */
  schema: FormSchemaV1 | null
  workspace: PublicWorkspace
  seo: PublicFormSeo
  /** Formalie's legal pages for the footer, platform settings (super admin, F23), config as fallback. */
  legal: { terms_url: string; privacy_url: string }
  /** The organisation's own privacy notice and consent line (Settings → Privacy and data, F14 M5). */
  privacy: { notice_url: string | null; consent: boolean; consent_text: string | null }
  /** Languages the form offers (its main language first) and the one served. */
  languages: string[]
  language: string
  /** Share settings (F10 M3): this visitor may not open the form yet, no questions are sent. */
  locked: boolean
  /** What opens it: password · personal invitation link · signing in as a member (null = not locked). */
  lock: 'password' | 'invite' | 'organisation' | null
  /** Who is filling in, when the form knows (invitation or signed-in member). */
  visitor: { name: string | null; email: string } | null
  /** Who may show the embed: the frame-ancestors value ("*" = any website). */
  embed_ancestors: string
}

/** POST /public/forms/{key}/submit → the response and what to show next. */
export interface PublicSubmitResult {
  response_id: string
  /** True when this fill-in session was already submitted (same Formalie-Key): nothing new was stored. */
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
       * already, this browser already sent one (offer "for someone else") · duplicate, the exact same
       * answers were already sent · registered, this person (their email / ID) already responded ·
       * possible, looks like an earlier response: ask "different person?" · verify, confirm the email first.
       */
      reason?: 'already' | 'duplicate' | 'registered' | 'possible' | 'verify'
      /** The identity question concerned, and a masked hint of the earlier response (never its details). */
      field?: string
      hint?: { at?: string; email?: string }
    }

/**
 * A file question's answer (F10 M2): the files are already in storage, the answer only holds a
 * reference per file (an encrypted id) plus what to show. Preview answers have an empty id.
 */
export interface FileAnswer {
  id: string
  name: string
  size: number
  type: string
}

/** Uploads one file for a file question, reporting progress (0–100); `onAbort` receives a cancel function. */
/**
 * A long list's options from the server as people type (F15 M3): matches for `q`, or the labels of chosen
 * `values`; a lower level of a large list (F15 M5) only what is under the choices above (`parents`).
 */
export type RendererLookup = (
  field: { key: string; option_set_id?: string | null; option_level?: number },
  query: { q: string; values?: string[]; parents?: string[] },
) => Promise<{ items: { value: string; label: string; attrs?: Record<string, string | number> }[]; total: number }>

export type RendererUpload = (field: string, file: File, onProgress: (percent: number) => void, onAbort: (abort: () => void) => void) => Promise<FileAnswer>

/** What the public page lets the renderer do for the respondent (F10). */
export interface RendererRespondent {
  /** The organisation (thank-you: "Visit … website") and whether the form is embedded in another site. */
  org?: { name: string; website: string | null }
  embedded?: boolean
  /** File questions: upload straight to storage (pre-signed link). */
  upload?: RendererUpload
  /** Long lists (F15 M3): ask the server for matching options. */
  lookup?: RendererLookup
  /** This browser already sent the form. */
  alreadySent: boolean
  /** Start a new response for someone else. */
  another: () => void
  /** "Yes, I'm a different person" (a similar earlier response exists). */
  confirmDifferent: () => void
  /** Email code step (forms that verify the respondent's email). */
  sendCode: (email: string) => Promise<{ sentTo: string; devCode: string | null } | null>
  confirmCode: (email: string, code: string) => Promise<boolean>
  /** Save and resume (forms that have it on). */
  resume?: {
    initial: { data: Record<string, unknown>; page: number } | null
    state: 'idle' | 'saving' | 'saved' | 'error'
    savedAt: string | null
    save: (data: Record<string, unknown>, page: number) => void
    later: (email: string) => Promise<{ sentTo: string | null; devUrl: string | null } | null>
  }
}

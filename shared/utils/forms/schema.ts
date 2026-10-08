/**
 * FormSchema v1 (docs/API-CONTRACT.md → FormSchema), validated on import and by the API.
 * Deliberately tolerant about field props (the builder, F7, owns the details) but strict about
 * structure, ids and sizes, so an imported file can never smuggle in something unexpected.
 */
import { z } from 'zod'
import { MAX_LIST_LEVELS, MAX_OPTIONS } from './options'

const id = z.string().regex(/^[A-Za-z0-9_-]{1,64}$/)
const text = (max: number) => z.string().max(max)

export const formFieldSchema = z.object({
  id,
  key: z.string().regex(/^[a-z][a-z0-9_]{0,63}$/),
  type: z.string().regex(/^[a-z_]{2,32}$/),
  label: text(500),
  placeholder: text(500).optional(),
  help: text(2000).optional(),
  width: z.number().int().min(1).max(12).optional(),
  required: z.boolean().optional(),
  /** Shown and submitted, but can't be changed (e.g. a prefilled reference). Never required. */
  readonly: z.boolean().optional(),
  /** Shown greyed out and not submitted. Never required. */
  disabled: z.boolean().optional(),
  /**
   * Field access, who the field is for. Everyone (default), or only some departments, job titles, roles or
   * people (`all` = every one of that kind). A restricted field is never required: people it is
   * not meant for must still be able to submit. Answers stay visible only to the same audience.
   */
  audience: z
    .object({
      mode: z.enum(['everyone', 'department', 'job_title', 'role', 'user']),
      all: z.boolean().optional(),
      ids: z.array(z.string().max(100)).max(500).optional(),
    })
    .optional(),
  validation: z.record(z.string(), z.unknown()).optional(),
  options: z
    .array(z.object({ value: text(200), label: text(500), score: z.number().finite().optional(), parent: text(200).optional() }))
    .max(MAX_OPTIONS)
    .nullable()
    .optional(),
  /** Public form page only (F15 M3): the options were left out, `total` of them; the page asks the server as people type. */
  options_remote: z.object({ total: z.number().int().min(0) }).nullable().optional(),
  option_set_id: z.string().nullable().optional(),
  /** Lists with levels (F15 M2, shared/utils/forms/cascade.ts): this field's level (0 = top) and the field one level up. */
  option_level: z.number().int().min(0).max(MAX_LIST_LEVELS - 1).optional(),
  option_parent: z.string().max(64).nullable().optional(),
  default: z.unknown().optional(),
  props: z.record(z.string(), z.unknown()).optional(),
})

export const formSchemaV1 = z.object({
  schema_version: z.literal(1),
  settings: z
    .object({
      progress_bar: z.boolean().optional(),
      save_resume: z.boolean().optional(),
      language: text(10).optional(),
      /** More languages the form offers besides its main one (F10 M4, decision 99). */
      languages: z.array(text(10)).max(19).optional(),
      /** The form title respondents see in the form language (empty = the form name). */
      title: text(200).optional(),
      /** Where labels sit, for the whole form: above the field (default) or beside it. */
      label_position: z.enum(['top', 'left']).optional(),
      /** An icon inside every field's box (its type's icon), for the whole form; default on (owner, 2026-10-06). */
      field_icons: z.boolean().optional(),
      /** Telling respondents apart (F10, shared/utils/forms/identity.ts): their own email, an ID, verification. */
      identity: z
        .object({ email: text(64).nullable(), verify: z.boolean() })
        .optional(),
      /** Keep responses for N days (F14 M5); missing = the workspace's default, 0 = keep them. */
      retention_days: z.number().int().min(0).max(3650).nullable().optional(),
      /** Response emails (F14 M4, shared/utils/forms/emails.ts): to team members, outside addresses, a copy for the respondent. */
      emails: z
        .object({
          team: z.array(z.string().max(64)).max(50),
          others: z.array(z.email().max(200)).max(20),
          others_personal: z.boolean(),
          receipt_field: text(64).nullable(),
        })
        .optional(),
      /** Help guide (F10, owner 2026-10-03): opened from a "?" button on the form; off by default. */
      guide: z.object({ enabled: z.boolean(), title: text(120), html: text(50_000) }).optional(),
    })
    .optional(),
  pages: z
    .array(
      z.object({
        id,
        title: text(200).optional(),
        rows: z.array(z.object({ id, fields: z.array(formFieldSchema).max(12) })).max(200),
      }),
    )
    .min(1)
    .max(50),
  logic: z.array(z.unknown()).max(500).optional(),
  /** Design tokens (shared/utils/forms/theme.ts); missing or invalid tokens use the workspace default. */
  theme: z.record(z.string(), z.unknown()).optional(),
  /** The saved theme this design came from (the tokens above are a copy). */
  theme_id: z.string().max(64).nullable().optional(),
  /** The page design the page around the form came from (the frame and page tokens are a copy). */
  page_design_id: z.string().max(64).nullable().optional(),
  calculations: z.array(z.unknown()).max(200).optional(),
  /** Translations per language: text key (shared/utils/forms/translations.ts) → text. */
  translations: z.record(z.string().max(10), z.record(z.string().max(200), z.string().max(50_000))).optional(),
  /** Per translation, a fingerprint of the text it was made from (changed text = "check the translation"). */
  translated_from: z.record(z.string().max(10), z.record(z.string().max(200), z.string().max(16))).optional(),
  thank_you: z
    .object({
      title: text(200).optional(),
      message: text(5000).optional(),
      redirect_url: z.url().nullable().optional(),
    })
    .optional(),
})

export type FormSchemaV1 = z.infer<typeof formSchemaV1>

/** Import file: `{ name?, schema }` (an export) or a bare schema. */
export const formImportFile = z.union([
  z.object({ name: text(120).optional(), schema: formSchemaV1 }),
  formSchemaV1.transform(schema => ({ name: undefined, schema })),
])

export const countFields = (schema: FormSchemaV1) =>
  schema.pages.reduce((sum, page) => sum + page.rows.reduce((n, row) => n + row.fields.length, 0), 0)

export const MAX_IMPORT_BYTES = 1024 * 1024

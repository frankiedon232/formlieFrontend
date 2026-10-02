/**
 * FormSchema v1 (docs/API-CONTRACT.md → FormSchema) — validated on import and by the API.
 * Deliberately tolerant about field props (the builder, F7, owns the details) but strict about
 * structure, ids and sizes, so an imported file can never smuggle in something unexpected.
 */
import { z } from 'zod'

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
  validation: z.record(z.string(), z.unknown()).optional(),
  options: z
    .array(z.object({ value: text(200), label: text(500) }))
    .max(500)
    .nullable()
    .optional(),
  option_set_id: z.string().nullable().optional(),
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
  calculations: z.array(z.unknown()).max(200).optional(),
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

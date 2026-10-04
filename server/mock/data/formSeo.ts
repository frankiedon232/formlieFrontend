/**
 * Search & link preview of a form (F10 M3, decision 95): what people see when the link is shared
 * (WhatsApp, LinkedIn, email…) and in search results. The creator may set a title, a description
 * and an image; empty = taken from the form (its title shown to respondents, its first text block
 * or header subtitle). One place for the public page and the Share tab.
 */
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import type { StoredForm } from './formStore'

export const SEO_TITLE_MAX = 70
export const SEO_DESCRIPTION_MAX = 200

/** Plain text from the first paragraph block (else the header subtitle). */
function summaryOf(schema: FormSchemaV1 | null | undefined): string {
  const intro = schema?.pages.flatMap(page => page.rows.flatMap(row => row.fields)).find(field => field.type === 'paragraph')
  const html = String((intro?.props as { html?: string } | undefined)?.html ?? '')
  const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  const subtitle = String((schema?.theme as { header?: { subtitle?: string } } | undefined)?.header?.subtitle ?? '').trim()
  return (text || subtitle).slice(0, SEO_DESCRIPTION_MAX)
}

/**
 * What the form says when nothing is set: its respondent title and intro (published version
 * first). `publishedOnly` (public pages): never the draft, so a form that was never published
 * shows only its name, no draft text.
 */
export function seoDefaults(form: StoredForm, publishedOnly = false): { title: string; description: string } {
  const schema = publishedOnly ? form.published_schema : (form.published_schema ?? form.schema)
  return { title: (schema?.settings?.title?.trim() || form.name).slice(0, SEO_TITLE_MAX), description: summaryOf(schema) }
}

/** The link preview as shown: the creator's text where set, the defaults otherwise. */
export function seoOf(form: StoredForm, publishedOnly = false): { title: string; description: string; imageUploadId: string | null; noindex: boolean } {
  const defaults = seoDefaults(form, publishedOnly)
  return {
    title: form.seo?.title?.trim() || defaults.title,
    description: form.seo?.description?.trim() || defaults.description,
    imageUploadId: form.seo?.image_upload_id ?? null,
    noindex: !!form.seo?.noindex,
  }
}

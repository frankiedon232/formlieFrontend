/**
 * The icon inside a field's box (owner, 2026-10-06: every field gets one, or none, for the whole
 * form). Each type's own icon, the same as in the builder's palette, with a few made clearer inside
 * a box. Fields without a box (choices as buttons, ratings, sliders, files, signatures) have none.
 * Currency shows its symbol and country its flag instead. For general fields the label decides first
 * (owner, 2026-10-06: "First name" → a person, "Company" → a building); the type's icon is the fallback.
 */
import type { InjectionKey, Ref } from 'vue'
import { FIELD_TYPES } from '#shared/utils/forms/fields'
import { iconFromLabel } from '#shared/utils/forms/label-icons'

/** Whether the form shows field icons (Form settings → Field icons), provided by the form and the builder canvas. */
export const RENDERER_ICONS: InjectionKey<Ref<boolean>> = Symbol('formalie:renderer-icons')

const IN_BOX: Record<string, string> = {
  dropdown: 'i-lucide-list',
  multi_select: 'i-lucide-list-checks',
  full_name: 'i-lucide-user',
  long_text: 'i-lucide-align-left',
  hidden: 'i-lucide-eye-off',
}
const NONE = new Set(['currency', 'country', 'radio', 'checkbox', 'toggle', 'ranking', 'matrix', 'consent', 'rating', 'scale', 'slider', 'file_upload', 'image_upload', 'signature', 'rich_text', 'payment'])

/** Types whose box can be anything: the label tells what it is. */
const BY_LABEL = new Set(['short_text', 'long_text', 'number', 'percentage', 'dropdown', 'multi_select', 'hidden', 'calculated', 'date', 'datetime', 'time', 'date_range'])

export function inputIconOf(field: { type: string; label?: string | null; key?: string | null }): string | undefined {
  if (NONE.has(field.type)) return undefined
  const fromLabel = BY_LABEL.has(field.type) ? iconFromLabel(field.label, field.key) : null
  return fromLabel ?? IN_BOX[field.type] ?? (FIELD_TYPES as Record<string, { icon: string }>)[field.type]?.icon
}

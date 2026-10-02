/**
 * Field type catalogue (FormSchema v1) — shared by the API mock (validation) and the app
 * (palette, inspector, renderer). Labels live in i18n under `builder.field.<type>`.
 * Adding a field type = one entry here + one in app/utils/forms/field-registry.ts + a renderer.
 */
export const FIELD_CATEGORIES = [
  'text',
  'dates',
  'choice',
  'rating',
  'files',
  'location',
  'technical',
  'advanced',
  'layout',
] as const
export type FieldCategory = (typeof FIELD_CATEGORIES)[number]

interface FieldTypeDefinition {
  category: FieldCategory
  icon: string
  /** Collects an answer (false for headings, dividers, images…). */
  input: boolean
  /** Has a list of options (inline or an option set). */
  options?: boolean
  /** Not available yet (shown in the palette as "soon"). */
  soon?: boolean
}

export const FIELD_TYPES = {
  // Text
  short_text: { category: 'text', icon: 'i-lucide-type', input: true },
  long_text: { category: 'text', icon: 'i-lucide-align-left', input: true },
  rich_text: { category: 'text', icon: 'i-lucide-text-quote', input: true },
  email: { category: 'text', icon: 'i-lucide-mail', input: true },
  phone: { category: 'text', icon: 'i-lucide-phone', input: true },
  url: { category: 'text', icon: 'i-lucide-link', input: true },
  number: { category: 'text', icon: 'i-lucide-hash', input: true },
  currency: { category: 'text', icon: 'i-lucide-banknote', input: true },
  full_name: { category: 'text', icon: 'i-lucide-id-card', input: true },
  percentage: { category: 'text', icon: 'i-lucide-percent', input: true },
  // Dates
  date: { category: 'dates', icon: 'i-lucide-calendar', input: true },
  time: { category: 'dates', icon: 'i-lucide-clock', input: true },
  datetime: { category: 'dates', icon: 'i-lucide-calendar-clock', input: true },
  date_range: { category: 'dates', icon: 'i-lucide-calendar-range', input: true },
  duration: { category: 'dates', icon: 'i-lucide-timer', input: true },
  // Choice
  dropdown: { category: 'choice', icon: 'i-lucide-chevron-down-square', input: true, options: true },
  multi_select: { category: 'choice', icon: 'i-lucide-list-checks', input: true, options: true },
  radio: { category: 'choice', icon: 'i-lucide-circle-dot', input: true, options: true },
  checkbox: { category: 'choice', icon: 'i-lucide-square-check', input: true, options: true },
  toggle: { category: 'choice', icon: 'i-lucide-toggle-right', input: true },
  ranking: { category: 'choice', icon: 'i-lucide-list-ordered', input: true, options: true },
  matrix: { category: 'choice', icon: 'i-lucide-grid-3x3', input: true, options: true },
  consent: { category: 'choice', icon: 'i-lucide-shield-check', input: true },
  // Rating
  rating: { category: 'rating', icon: 'i-lucide-star', input: true },
  scale: { category: 'rating', icon: 'i-lucide-gauge', input: true },
  slider: { category: 'rating', icon: 'i-lucide-sliders-horizontal', input: true },
  // Files
  file_upload: { category: 'files', icon: 'i-lucide-paperclip', input: true },
  image_upload: { category: 'files', icon: 'i-lucide-image-up', input: true },
  signature: { category: 'files', icon: 'i-lucide-signature', input: true },
  // Location
  address: { category: 'location', icon: 'i-lucide-map-pin', input: true },
  country: { category: 'location', icon: 'i-lucide-globe', input: true },
  language: { category: 'location', icon: 'i-lucide-languages', input: true },
  timezone: { category: 'location', icon: 'i-lucide-clock-4', input: true },
  currency_code: { category: 'location', icon: 'i-lucide-coins', input: true },
  // Technical & IDs
  ip_address: { category: 'technical', icon: 'i-lucide-network', input: true },
  domain: { category: 'technical', icon: 'i-lucide-globe-lock', input: true },
  mac_address: { category: 'technical', icon: 'i-lucide-cpu', input: true },
  color: { category: 'technical', icon: 'i-lucide-palette', input: true },
  iban: { category: 'technical', icon: 'i-lucide-landmark', input: true },
  bic: { category: 'technical', icon: 'i-lucide-building-2', input: true },
  // Advanced
  hidden: { category: 'advanced', icon: 'i-lucide-eye-off', input: true },
  calculated: { category: 'advanced', icon: 'i-lucide-calculator', input: true },
  payment: { category: 'advanced', icon: 'i-lucide-credit-card', input: true, soon: true },
  // Layout
  section: { category: 'layout', icon: 'i-lucide-heading', input: false },
  paragraph: { category: 'layout', icon: 'i-lucide-pilcrow', input: false },
  divider: { category: 'layout', icon: 'i-lucide-minus', input: false },
  image: { category: 'layout', icon: 'i-lucide-image', input: false },
} as const satisfies Record<string, FieldTypeDefinition>

export type FieldType = keyof typeof FIELD_TYPES
export const FIELD_TYPE_KEYS = Object.keys(FIELD_TYPES) as FieldType[]

export const isFieldType = (value: string): value is FieldType => value in FIELD_TYPES
export const isInputField = (type: string) =>
  (FIELD_TYPES as Record<string, FieldTypeDefinition>)[type]?.input ?? false
export const hasOptions = (type: string) =>
  !!(FIELD_TYPES as Record<string, FieldTypeDefinition>)[type]?.options

/** 12-column grid widths offered in the builder (full, ½, ⅓, ⅔, ¼, ¾). */
export const FIELD_WIDTHS = [12, 6, 4, 8, 3, 9] as const

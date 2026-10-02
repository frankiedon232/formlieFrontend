/**
 * Builder side of each field type (FRONTEND-SPEC §6): default settings for a new field and which
 * inspector controls apply. The type list itself is shared (shared/utils/forms/fields.ts);
 * labels come from i18n `builder.field.<type>`. One entry per type — the palette, inspector and
 * renderer all read from here.
 */
import type { FormField } from '#shared/utils/forms/build'
import { FIELD_TYPES, type FieldType } from '#shared/utils/forms/fields'

/** Inspector controls a field type offers (sections show only when they apply). */
export type InspectorControl =
  | 'label'
  | 'placeholder'
  | 'help'
  | 'required'
  | 'width'
  | 'default_text'
  | 'default_toggle'
  | 'options'
  | 'length'
  | 'range'
  | 'pattern'
  | 'files'
  | 'selection_count'
  | 'scale'
  | 'rating'
  | 'slider'
  | 'currency'
  | 'matrix_rows'
  | 'content'
  | 'collapsible'
  | 'rich_toolbar'
  | 'image'
  | 'formula'
  | 'prefill'

interface RegistryEntry {
  controls: InspectorControl[]
  /** Settings for a fresh field of this type (label added from i18n). */
  defaults: Partial<FormField>
}

const TEXT: InspectorControl[] = [
  'label',
  'placeholder',
  'help',
  'required',
  'width',
  'default_text',
  'prefill',
]
const CHOICE: InspectorControl[] = ['label', 'help', 'required', 'width', 'options', 'prefill']
const sample = (...labels: string[]) => labels.map((label, i) => ({ value: `option_${i + 1}`, label }))

export const FIELD_REGISTRY: Record<FieldType, RegistryEntry> = {
  short_text: { controls: [...TEXT, 'length', 'pattern'], defaults: {} },
  long_text: { controls: [...TEXT, 'length'], defaults: { props: { rows: 4 } } },
  rich_text: {
    controls: ['label', 'help', 'placeholder', 'required', 'width', 'length', 'rich_toolbar'],
    defaults: { props: { toolbar: 'basic' } },
  },
  email: { controls: TEXT, defaults: { placeholder: 'name@example.com' } },
  phone: { controls: TEXT, defaults: { placeholder: '+44 7700 900123' } },
  url: { controls: TEXT, defaults: { placeholder: 'https://' } },
  number: { controls: [...TEXT, 'range'], defaults: {} },
  currency: { controls: [...TEXT, 'range', 'currency'], defaults: { props: { currency: 'USD' } } },
  date: { controls: ['label', 'help', 'required', 'width', 'prefill'], defaults: {} },
  time: { controls: ['label', 'help', 'required', 'width', 'prefill'], defaults: {} },
  datetime: { controls: ['label', 'help', 'required', 'width', 'prefill'], defaults: {} },
  date_range: { controls: ['label', 'help', 'required', 'width'], defaults: {} },
  dropdown: {
    controls: [...CHOICE, 'placeholder'],
    defaults: { options: sample('Option 1', 'Option 2', 'Option 3') },
  },
  multi_select: {
    controls: [...CHOICE, 'placeholder', 'selection_count'],
    defaults: { options: sample('Option 1', 'Option 2', 'Option 3') },
  },
  radio: { controls: CHOICE, defaults: { options: sample('Option 1', 'Option 2', 'Option 3') } },
  checkbox: {
    controls: [...CHOICE, 'selection_count'],
    defaults: { options: sample('Option 1', 'Option 2', 'Option 3') },
  },
  toggle: { controls: ['label', 'help', 'required', 'width', 'default_toggle', 'prefill'], defaults: {} },
  ranking: {
    controls: ['label', 'help', 'required', 'width', 'options'],
    defaults: { options: sample('First', 'Second', 'Third') },
  },
  matrix: {
    controls: ['label', 'help', 'required', 'width', 'options', 'matrix_rows'],
    defaults: {
      options: sample('Poor', 'Fair', 'Good', 'Excellent'),
      props: { rows: ['Quality', 'Speed', 'Value'] },
    },
  },
  rating: { controls: ['label', 'help', 'required', 'width', 'rating'], defaults: { props: { max: 5 } } },
  scale: {
    controls: ['label', 'help', 'required', 'width', 'scale'],
    defaults: { props: { min: 0, max: 10, min_label: '', max_label: '' } },
  },
  slider: {
    controls: ['label', 'help', 'required', 'width', 'slider'],
    defaults: { props: { min: 0, max: 100, step: 1 } },
  },
  file_upload: {
    controls: ['label', 'help', 'required', 'width', 'files'],
    defaults: { props: { max_files: 1, max_mb: 10, accept: '' } },
  },
  image_upload: {
    controls: ['label', 'help', 'required', 'width', 'files'],
    defaults: { props: { max_files: 1, max_mb: 10, accept: 'image/*' } },
  },
  signature: { controls: ['label', 'help', 'required', 'width'], defaults: {} },
  address: { controls: ['label', 'help', 'required', 'width'], defaults: {} },
  country: { controls: ['label', 'help', 'required', 'width', 'placeholder', 'prefill'], defaults: {} },
  hidden: { controls: ['label', 'default_text', 'prefill'], defaults: { props: { param: '' } } },
  calculated: { controls: ['label', 'help', 'width', 'formula'], defaults: { props: { formula: '' } } },
  payment: { controls: ['label', 'help', 'required'], defaults: {} },
  section: { controls: ['label', 'content', 'collapsible'], defaults: { props: { description: '' } } },
  paragraph: { controls: ['content', 'width'], defaults: { props: { text: '' } } },
  divider: { controls: [], defaults: {} },
  image: { controls: ['image', 'width'], defaults: { props: { src: '', alt: '' } } },
}

export const fieldIcon = (type: string) =>
  (FIELD_TYPES as Record<string, { icon: string }>)[type]?.icon ?? 'i-lucide-square'

export const hasControl = (type: string, control: InspectorControl) =>
  FIELD_REGISTRY[type as FieldType]?.controls.includes(control) ?? false

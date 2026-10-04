import type { FormField } from '#shared/utils/forms/build'
import type { AddressPart, ValidationIssue } from '#shared/utils/forms/validate'

const PART_LABEL: Record<AddressPart, string> = {
  line1: 'renderer.address.line1',
  city: 'renderer.address.city',
  region: 'renderer.address.region',
  postal_code: 'renderer.address.postalCode',
  country: 'renderer.address.country',
}

/** Renderer: an answer's problem in words (the API runs the same rules, shared/utils/forms/validate.ts). */
export function useAnswerMessages() {
  const { t } = useI18n()
  return function message(field: FormField, issue: ValidationIssue) {
    const name = field.label?.trim() || t('builder.untitled')
    if (issue.code === 'required')
      return field.label?.trim() ? t('renderer.requiredNamed', { field: name }) : t('renderer.requiredError')
    if (issue.code === 'address')
      return t('renderer.invalid.address', { field: name, parts: (issue.parts ?? []).map(part => t(PART_LABEL[part])).join(', ') })
    const custom = field.validation?.pattern_message
    if (issue.code === 'pattern' && typeof custom === 'string' && custom.trim()) return custom
    return t(`renderer.invalid.${issue.code}`, { field: name, ...issue.params })
  }
}

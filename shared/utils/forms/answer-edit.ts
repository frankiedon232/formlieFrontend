/**
 * Editing a submitted answer (F11 M2): which questions a team member can change after the fact,
 * the same rule for the response panel and the API. Files, signatures and payments are evidence
 * from the respondent, calculated answers follow from the others and hidden values come from the
 * link, so none of those can be edited.
 */
import type { FormField } from './build'
import { isInputField } from './fields'

const LOCKED = new Set(['file_upload', 'image_upload', 'signature', 'payment', 'calculated', 'hidden'])

export const canEditAnswer = (field: Pick<FormField, 'type'>) => isInputField(field.type) && !LOCKED.has(field.type)

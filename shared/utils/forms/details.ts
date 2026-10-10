/**
 * List details in formulas and logic (leftovers L1, owner 2026-10-10). Options of a list may carry details
 * (`attrs`, F15 M4), such as a product's price or a branch's region. They can now be used directly:
 *
 *   formula    {product.price} * {quantity}         the chosen option's price (several chosen: their sum)
 *   condition  { field, detail: 'region', op: 'eq', value: 'North' }
 *
 * One choice gives its detail; several choices give the sum when every detail is a number, else the list
 * of details. Nothing chosen, or a chosen option without that detail, counts as no answer. The same code
 * runs on the form page and on the server.
 */
import type { FormField } from './build'
import type { PickedOptions } from './fills'

type Attr = string | number
export type DetailAnswer = number | string | string[] | null
type OptionLike = { value: string; attrs?: Record<string, Attr> }

/** The options a field chooses from (a large list's options come from what the page learned). */
const optionsOf = (field: Pick<FormField, 'id' | 'options'>, picked?: PickedOptions): OptionLike[] =>
  (field.options?.length ? field.options : (picked?.[field.id] ?? [])) as OptionLike[]

const asNumber = (attr: Attr) => (typeof attr === 'number' ? attr : Number(String(attr).trim().replace(',', '.')))
const isNumber = (attr: Attr) => String(attr).trim() !== '' && Number.isFinite(asNumber(attr))

/** The details of the chosen option(s) for one column; null when nothing is chosen. */
export function chosenDetails(field: Pick<FormField, 'id' | 'options'>, answer: unknown, column: string, picked?: PickedOptions): Attr[] | null {
  const chosen = Array.isArray(answer) ? answer.map(String) : answer == null || answer === '' ? [] : [String(answer)]
  if (!chosen.length) return null
  const options = optionsOf(field, picked)
  return chosen.map(value => options.find(option => option.value === value)?.attrs?.[column]).filter((attr): attr is Attr => attr !== undefined && attr !== '')
}

/** What a condition on a detail tests: a number, a text, a list of texts (several chosen) or null. */
export function detailAnswer(field: Pick<FormField, 'id' | 'options'>, answer: unknown, column: string, picked?: PickedOptions): DetailAnswer {
  const details = chosenDetails(field, answer, column, picked)
  if (!details?.length) return null
  if (details.every(isNumber)) return details.reduce<number>((sum, attr) => sum + asNumber(attr), 0)
  return Array.isArray(answer) ? details.map(String) : String(details[0])
}

/** Does a column hold numbers on every option that has it (so it is compared and added up as a number)? */
export function isNumericDetail(field: Pick<FormField, 'options'>, column: string): boolean {
  const values = ((field.options ?? []) as OptionLike[]).map(option => option.attrs?.[column]).filter((attr): attr is Attr => attr !== undefined && attr !== '')
  return values.length > 0 && values.every(isNumber)
}

/** Detail columns the field's options carry (keys only; the builder adds the list's labels). */
export const detailKeysOf = (field: Pick<FormField, 'options'>): string[] => [...new Set(((field.options ?? []) as OptionLike[]).flatMap(option => Object.keys(option.attrs ?? {})))]

/**
 * Filtering responses by their answers (F11 M2), one rule for the list and the API. Questions
 * with a short set of answers get a filter of their own: choices (their options), yes / no, and
 * ratings or scales of up to 11 steps (each score). `filter[a_{key}]=v1,v2` keeps responses whose
 * answer is any of them (for several picks: any of them picked); `filter[empty]=k1,k2` keeps those
 * that left every listed question unanswered.
 */
import type { FormField } from './build'

const CHOICES = new Set(['dropdown', 'radio', 'checkbox', 'multi_select'])
export const ANSWER_FILTER_PREFIX = 'a_'

/** The values a question can be filtered on, or null when it gets no filter of its own. */
export function filterValues(field: Pick<FormField, 'type' | 'options' | 'props'>): string[] | null {
  if (CHOICES.has(field.type)) return field.options?.length ? field.options.map(option => option.value) : null
  if (field.type === 'toggle') return ['true', 'false']
  if (field.type === 'rating' || field.type === 'scale') {
    const min = field.type === 'rating' ? 1 : Number(field.props?.min ?? 0)
    const max = Number(field.props?.max ?? (field.type === 'rating' ? 5 : 10))
    return max - min <= 10 && max >= min ? Array.from({ length: max - min + 1 }, (_, i) => String(min + i)) : null
  }
  return null
}

/** An answer as the strings a filter compares with. */
export const answerValues = (value: unknown): string[] =>
  value == null || value === '' ? [] : Array.isArray(value) ? value.map(String) : [String(value)]

export const answerMatches = (value: unknown, wanted: string[]) => answerValues(value).some(item => wanted.includes(item))

export const isEmptyAnswer = (value: unknown) => answerValues(value).length === 0 || (typeof value === 'object' && !Array.isArray(value) && value !== null && Object.values(value).every(part => part == null || part === ''))

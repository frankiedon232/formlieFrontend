/**
 * The questions fill-in analytics follows, in form order with their page (0-based schema page
 * index): every field people answer themselves, so no display blocks, hidden fields or calculated
 * fields. The fill-in page records answers only for these; the funnel and drop-off use the same list.
 */
import { isInputField } from '../forms/fields'
import type { FormSchemaV1 } from '../forms/schema'
import type { FunnelQuestionRef } from './events'

const NOT_ANSWERED_BY_PEOPLE = new Set(['hidden', 'calculated'])

export const isTrackedQuestion = (type: string) => isInputField(type) && !NOT_ANSWERED_BY_PEOPLE.has(type)

export function funnelQuestions(schema: Pick<FormSchemaV1, 'pages'>): FunnelQuestionRef[] {
  return schema.pages.flatMap((page, index) =>
    page.rows.flatMap(row => row.fields.filter(field => isTrackedQuestion(field.type)).map(field => ({ key: field.key, page: index }))),
  )
}

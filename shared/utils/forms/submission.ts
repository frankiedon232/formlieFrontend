/**
 * A whole submission, checked the way the renderer checks it page by page (F10). The browser runs
 * it before sending; the API runs it again on what arrives, so a changed or hand-made request
 * can't skip a required question or slip in a value the form doesn't have.
 *
 *   - only pages on the respondent's path count (hidden pages and jumped-over pages are skipped)
 *   - hidden, read-only, disabled and restricted fields are never required
 *   - calculated fields are worked out again from the answers (the client's values are ignored)
 *   - answers for unknown fields are dropped
 */
import { allFields, cannotBeRequired, isLocked, type FormField } from './build'
import { isInputField } from './fields'
import { cascadeClosed, fitAnswer } from './cascade'
import { calculateResult } from './formula'
import { END_OF_FORM, evaluateLogic, type LogicState } from './logic'
import type { FormSchemaV1 } from './schema'
import { validateAnswer, type ValidationIssue } from './validate'

/** The field as respondents get it right now (logic can disable / enable it and change "required"). */
export function effectiveField(field: FormField, logic: LogicState): FormField {
  const disabled = logic.disabled.has(field.id) ? true : logic.enabled.has(field.id) ? false : field.disabled
  const wanted = logic.optional.has(field.id) ? false : !!field.required || logic.required.has(field.id)
  const required = wanted && !cannotBeRequired({ ...field, disabled })
  return { ...field, disabled, required }
}

/** Index of the page after `index` (jumps and hidden pages applied); -1 = end of the form. */
export function nextPageIndex(schema: FormSchemaV1, logic: LogicState, index: number): number {
  const page = schema.pages[index]
  const jump = page && logic.jumps.get(page.id)
  if (jump === END_OF_FORM) return -1
  const target = jump ? schema.pages.findIndex(p => p.id === jump) : -1
  const from = target > index ? target : index + 1
  return schema.pages.findIndex((p, i) => i >= from && !logic.hiddenPages.has(p.id))
}

/** Pages a respondent passes through with these answers. */
export function pathPages(schema: FormSchemaV1, logic: LogicState): number[] {
  const path: number[] = []
  let index = schema.pages.findIndex(p => !logic.hiddenPages.has(p.id))
  while (index >= 0 && !path.includes(index)) {
    path.push(index)
    index = nextPageIndex(schema, logic, index)
  }
  return path
}

/** Answers with calculated fields worked out again (and logic's "set value" applied). */
export function settleAnswers(schema: FormSchemaV1, input: Record<string, unknown>): Record<string, unknown> {
  const fields = allFields(schema)
  const byKey = new Map(fields.map(f => [f.key, f]))
  const answers: Record<string, unknown> = {}
  for (const field of fields) if (isInputField(field.type) && field.key in input) answers[field.key] = input[field.key]
  // Two passes: set values and calculations can depend on each other once.
  for (let pass = 0; pass < 2; pass++) {
    const logic = evaluateLogic(schema, answers)
    for (const [id, value] of logic.values) {
      const field = fields.find(f => f.id === id)
      if (field) answers[field.key] = value
    }
    for (const field of fields)
      if (field.type === 'calculated') answers[field.key] = calculateResult(String(field.props?.formula ?? ''), answers, byKey)
  }
  return answers
}

export interface SubmissionIssue extends ValidationIssue {
  key: string
}

/** Every problem with a submission (empty when it can be stored) and the answers to store. */
export function checkSubmission(schema: FormSchemaV1, input: Record<string, unknown>): { issues: SubmissionIssue[]; answers: Record<string, unknown> } {
  const settled = settleAnswers(schema, input)
  // Lists with levels: a level only counts when it has something under the choice above (F15 M2)
  const byId = new Map(allFields(schema).map(item => [item.id, item]))
  const dropped = new Set<string>()
  for (const field of byId.values()) {
    if (!field.option_parent) continue
    const fitted = fitAnswer(field, byId, settled)
    if (fitted === undefined) dropped.add(field.key)
    settled[field.key] = fitted
  }
  const answers = Object.fromEntries(Object.entries(settled).filter(([key]) => !dropped.has(key)))
  const logic = evaluateLogic(schema, answers)
  const issues: SubmissionIssue[] = []
  for (const index of pathPages(schema, logic))
    for (const row of schema.pages[index]!.rows)
      for (const raw of row.fields as FormField[]) {
        if (logic.hidden.has(raw.id) || cascadeClosed(raw, byId, answers)) continue
        const field = effectiveField(raw, logic)
        if (!isInputField(field.type) || field.type === 'hidden' || field.type === 'calculated' || isLocked(field)) continue
        const issue = validateAnswer(field, answers[field.key], !!field.required)
        if (issue) issues.push({ key: field.key, ...issue })
      }
  return { issues, answers }
}

/**
 * Lists with levels in the renderer (F15 M2): the form shares its live answers and fields so a level
 * field can offer only the options under what was chosen above (shared/utils/forms/cascade.ts).
 * Absent (builder canvas) = every option shows.
 */
import type { InjectionKey, Ref } from 'vue'
import type { FormField } from '#shared/utils/forms/build'

export interface RendererAnswers {
  answers: Ref<Record<string, unknown>>
  fieldsById: Ref<Map<string, FormField>>
}
export const RENDERER_ANSWERS: InjectionKey<RendererAnswers> = Symbol('formalie:renderer-answers')

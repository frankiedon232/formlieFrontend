/**
 * Lists with levels in the renderer (F15 M2): the form shares its live answers and fields so a level
 * field can offer only the options under what was chosen above (shared/utils/forms/cascade.ts).
 * The builder canvas provides its try-out answers the same way, so levels behave there as in the form.
 */
import type { InjectionKey, Ref } from 'vue'
import type { FormField } from '#shared/utils/forms/build'
import type { PickedOptions } from '#shared/utils/forms/fills'

export interface RendererAnswers {
  answers: Ref<Record<string, unknown>>
  fieldsById: Ref<Map<string, FormField>>
  /** Options chosen from lists kept on the server, with their details (auto-fill in the browser). */
  picked?: Ref<PickedOptions>
}
export const RENDERER_ANSWERS: InjectionKey<RendererAnswers> = Symbol('formalie:renderer-answers')

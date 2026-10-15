import { answeredSince } from '#shared/utils/analytics/recorder'
import { funnelQuestions } from '#shared/utils/analytics/questions'
import type { FormSchemaV1 } from '#shared/utils/forms/schema'
import type { RendererRespondent } from '#shared/types/public'

/**
 * Renderer: tells the public page's analytics (respondent.track) which page is shown (multi-page
 * forms) and which question got a value for the first time. Starting values (defaults, link
 * prefill, a restored draft) never count. Previews pass no `track`, so nothing happens there.
 */
export function useRendererTracking(options: {
  schema: () => FormSchemaV1
  answers: Ref<Record<string, unknown>>
  index: Ref<number>
  done: Ref<boolean>
  track: () => RendererRespondent['track'] | undefined
}) {
  const snapshot = () => JSON.parse(JSON.stringify(options.answers.value)) as Record<string, unknown>
  let baseline = snapshot()
  const keys = computed(() => funnelQuestions(options.schema()).map(question => question.key))

  watch(
    options.index,
    index => {
      if (options.schema().pages.length > 1 && !options.done.value) options.track()?.page(index)
    },
    { immediate: true },
  )
  watch(
    options.answers,
    values => {
      const track = options.track()
      if (!track || options.done.value) return
      for (const key of answeredSince(values, baseline, keys.value)) track.answer(key)
    },
    { deep: true },
  )

  /** Answers were reset or restored (a new fill-in, a draft): they are the new starting point. */
  return { rebase: () => (baseline = snapshot()) }
}

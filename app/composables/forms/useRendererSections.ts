import { sectionOwners, type FormField, type FormPage } from '#shared/utils/forms/build'
import type { evaluateLogic } from '#shared/utils/forms/logic'
import { effectiveField } from '#shared/utils/forms/submission'

/**
 * Renderer: the rows of the current page as respondents get them (logic applied, hidden and
 * internal fields left out) and collapsible sections. A section heading with `collapsible` folds
 * the rows below it, up to the next section; folded fields still count for required checks (a
 * failing one unfolds its section, see `unfoldFor`).
 */
export function useRendererSections(
  page: Ref<FormPage | undefined>,
  logic: Ref<ReturnType<typeof evaluateLogic>>,
  allFields: Ref<Map<string, FormField>>,
) {
  const visibleRows = computed(() =>
    (page.value?.rows ?? [])
      .map(row => ({
        ...row,
        // Internal calculations (e.g. a loyalty group) are worked out and saved, but not shown.
        fields: (row.fields as FormField[])
          .filter(f => !logic.value.hidden.has(f.id) && !(f.type === 'calculated' && f.props?.internal))
          .map(field => effectiveField(field, logic.value)),
      }))
      .filter(row => row.fields.length),
  )

  const collapsible = (field?: FormField) => field?.type === 'section' && !!field.props?.collapsible
  const folded = ref<Record<string, boolean>>({})
  watch(
    () => [...allFields.value.values()].filter(collapsible),
    sections => {
      for (const section of sections) folded.value[section.id] ??= !!section.props?.collapsed
    },
    { immediate: true },
  )
  const ownerOf = computed(() => sectionOwners(visibleRows.value))
  /** What's on screen: hidden-type fields carry values but are never shown to respondents. */
  const shownRows = computed(() =>
    visibleRows.value
      .filter(row => !folded.value[ownerOf.value.get(row.id) ?? ''])
      .map(row => ({ ...row, fields: row.fields.filter(f => f.type !== 'hidden') }))
      .filter(row => row.fields.length),
  )
  const toggle = (id: string) => (folded.value[id] = !folded.value[id])
  /** Open every section that holds a question with an error. */
  function unfoldFor(errors: Record<string, string>) {
    for (const row of visibleRows.value) {
      const owner = ownerOf.value.get(row.id)
      if (owner && row.fields.some(f => errors[f.key])) folded.value[owner] = false
    }
  }
  return { visibleRows, shownRows, collapsible, folded, toggle, unfoldFor }
}

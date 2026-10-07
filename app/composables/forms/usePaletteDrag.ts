import type { FormField } from '#shared/utils/forms/build'

/**
 * Dragging from a palette list onto the canvas: the clone callback builds the new field
 * (`track`), and when the drop lands (`end`) that field is selected. Shared by the Fields, Saved
 * and Lists tabs.
 */
export function usePaletteDrag(onPlaced: () => void) {
  const builder = useBuilder()
  let dragged: FormField | null = null
  // A list with levels: the levels below the dragged top one, added beside it on drop
  let rest: FormField[] = []

  function track(field: FormField, others: FormField[] = []): FormField {
    dragged = field
    rest = others
    return field
  }
  function start() {
    builder.history.record()
    builder.dragging.value = true
  }
  function end() {
    builder.dragging.value = false
    if (dragged && builder.findField(dragged.id)) {
      if (rest.length) builder.attachChain(dragged, rest)
      builder.select(dragged.id)
      onPlaced()
    }
    dragged = null
    rest = []
  }
  return { start, track, end }
}

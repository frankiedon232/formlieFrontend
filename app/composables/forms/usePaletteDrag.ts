import type { FormField } from '#shared/utils/forms/build'

/**
 * Dragging from a palette list onto the canvas: the clone callback builds the new field
 * (`track`), and when the drop lands (`end`) that field is selected. Shared by the Fields, Saved
 * and Lists tabs.
 */
export function usePaletteDrag(onPlaced: () => void) {
  const builder = useBuilder()
  let dragged: string | null = null

  function track(field: FormField): FormField {
    dragged = field.id
    return field
  }
  function start() {
    builder.history.record()
    builder.dragging.value = true
  }
  function end() {
    builder.dragging.value = false
    if (dragged && builder.findField(dragged)) {
      builder.select(dragged)
      onPlaced()
    }
    dragged = null
  }
  return { start, track, end }
}

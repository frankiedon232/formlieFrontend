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
  function end() {
    if (dragged && builder.findField(dragged)) {
      builder.select(dragged)
      onPlaced()
    }
    dragged = null
  }
  return { track, end }
}

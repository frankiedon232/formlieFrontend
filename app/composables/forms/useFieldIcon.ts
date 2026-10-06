/** The icon for a field's box (from its label, else its type), or nothing when the form hides field icons. */
export function useFieldIcon(field: MaybeRefOrGetter<{ type: string; label?: string | null; key?: string | null }>) {
  const shown = inject(RENDERER_ICONS, ref(true))
  return computed(() => (shown.value ? inputIconOf(toValue(field)) : undefined))
}

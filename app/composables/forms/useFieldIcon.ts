/** The icon for a field's box, or nothing when the form hides field icons (default: shown). */
export function useFieldIcon(type: MaybeRefOrGetter<string>) {
  const shown = inject(RENDERER_ICONS, ref(true))
  return computed(() => (shown.value ? inputIconOf(toValue(type)) : undefined))
}

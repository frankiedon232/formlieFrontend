import type { SavedTheme } from '#shared/types/forms'
import type { FormTheme, ThemePatch } from '#shared/utils/forms/theme'

/**
 * The designer's model on top of the builder schema (F8). The resolved theme is read from
 * `schema.theme`; every change writes the full theme back (one undo step per control, typing
 * grouped), so the published form looks exactly like the preview. "Reset" removes the stored
 * theme, the form then follows the workspace default again (brand colour + logo).
 */
export function useDesigner() {
  const builder = useBuilder()
  const branding = useWorkspaceBranding()
  const theme = useFormTheme(() => builder.schema.value?.theme)
  const customised = computed(() => !!builder.schema.value?.theme)

  function write(next: FormTheme, group?: string) {
    if (!builder.schema.value) return
    builder.history.record(group)
    builder.schema.value.theme = structuredClone(toRaw(next)) as unknown as Record<string, unknown>
  }

  /** Set one token: `set('colors', 'primary', '#123456')`. */
  function set<G extends keyof FormTheme, K extends keyof FormTheme[G]>(group: G, key: K, value: FormTheme[G][K]) {
    const next = structuredClone(toRaw(theme.value))
    ;(next[group] as FormTheme[G])[key] = value
    write(next, `theme:${String(group)}.${String(key)}`)
  }
  const setLayout = (layout: FormTheme['layout']) => write({ ...structuredClone(toRaw(theme.value)), layout })

  /** Apply a starting point over the workspace default (keeps nothing of the old design). */
  function applyPreset(patch: ThemePatch) {
    write(applyPatch(resolveTheme(undefined, branding.value), patch))
    if (builder.schema.value) builder.schema.value.theme_id = null
  }

  /** Apply a saved theme: copy its tokens and remember where they came from. */
  function applySaved(saved: SavedTheme) {
    write(resolveTheme(saved.tokens, branding.value))
    if (builder.schema.value) builder.schema.value.theme_id = saved.id
  }
  const themeId = computed(() => builder.schema.value?.theme_id ?? null)

  function reset() {
    if (!builder.schema.value?.theme) return
    builder.history.record()
    delete builder.schema.value.theme
    delete builder.schema.value.theme_id
  }

  return { theme, customised, themeId, set, setLayout, applyPreset, applySaved, reset, write }
}

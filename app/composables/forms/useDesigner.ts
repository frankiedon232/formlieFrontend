import type { PageDesign, SavedTheme } from '#shared/types/forms'
import { pageTokensOf, withPageDesign } from '#shared/utils/forms/page-design'
import type { FormTheme, ThemePatch } from '#shared/utils/forms/theme'

/**
 * The designer's model on top of the builder schema (F8). The resolved theme is read from
 * `schema.theme`; every change writes the full theme back (one undo step per control, typing
 * grouped), so the published form looks exactly like the preview. "Reset" removes the stored
 * theme, the form then follows the workspace default again (brand colour + logo).
 * Page designs (owner 2026-10-04) change only the page around the form; with one applied, picking a
 * theme or a starting point keeps that page, so a theme and a page design combine.
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
  /** Keep the page around the form when a page design is applied. */
  const keepPage = (next: FormTheme) => (builder.schema.value?.page_design_id ? withPageDesign(next, pageTokensOf(theme.value)) : next)

  function applyPreset(patch: ThemePatch) {
    write(keepPage(applyPatch(resolveTheme(undefined, branding.value), patch)))
    if (builder.schema.value) builder.schema.value.theme_id = null
  }

  /** Apply a saved theme: copy its tokens and remember where they came from. */
  function applySaved(saved: SavedTheme) {
    write(keepPage(resolveTheme(saved.tokens, branding.value)))
    if (builder.schema.value) builder.schema.value.theme_id = saved.id
  }

  /** Apply a page design: only the page around the form changes; remember where it came from. */
  function applyPage(page: PageDesign) {
    write(withPageDesign(theme.value, page.tokens))
    if (builder.schema.value) builder.schema.value.page_design_id = page.id
  }
  const pageDesignId = computed(() => builder.schema.value?.page_design_id ?? null)
  const themeId = computed(() => builder.schema.value?.theme_id ?? null)

  function reset() {
    if (!builder.schema.value?.theme) return
    builder.history.record()
    delete builder.schema.value.theme
    delete builder.schema.value.theme_id
    delete builder.schema.value.page_design_id
  }

  return { theme, customised, themeId, pageDesignId, set, setLayout, applyPreset, applySaved, applyPage, reset, write }
}

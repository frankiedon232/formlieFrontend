/**
 * The builder's side panes on large screens (owner 2026-10-08): Fields (start) and Settings (end) open
 * by default, each can be collapsed for a wider canvas and opened again from the toggles beside the
 * page tabs. Kept in this browser (a display preference only). Selecting a field opens Settings.
 */
export function useBuilderPanes() {
  const fields = useLocalStorage('formalie-builder-palette', true)
  const settings = useLocalStorage('formalie-builder-inspector', true)
  return { fields, settings }
}

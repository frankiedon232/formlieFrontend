/**
 * Every keyboard shortcut, grouped (the "?" dialog shows general and navigation; Help & support → Keyboard
 * shortcuts shows them all). Navigation follows the menu, so it only lists places this person can open.
 */
export interface ShortcutItem {
  label: string
  keys: string[]
  /** Press the keys one after the other (G then F), not together. */
  chain?: boolean
}

/** An area's "Overview" is named by its area, so the list never shows two Overviews. */
const AREA_NAMES: Record<string, string> = { dataOverview: 'nav.dataSources', apiOverview: 'nav.apiService', aiOverview: 'nav.ai' }

export function useShortcutList() {
  const { t } = useI18n()
  const { destinations } = useNavigation()

  const general = computed(() => ({
    key: 'general',
    title: t('shortcuts.general'),
    items: [
      { label: t('shortcuts.search'), keys: ['meta', 'k'] },
      { label: t('shortcuts.help'), keys: ['?'] },
      { label: t('shortcuts.toggleSidebar'), keys: ['['] },
      { label: t('shortcuts.closeOverlay'), keys: ['escape'] },
    ] as ShortcutItem[],
  }))
  const navigation = computed(() => ({
    key: 'navigation',
    title: t('shortcuts.navigation'),
    items: destinations.value.filter(item => item.shortcut).map(item => ({ label: AREA_NAMES[item.key] ? t(AREA_NAMES[item.key]!) : t(`nav.${item.key}`), keys: item.shortcut!.split('-'), chain: true })) as ShortcutItem[],
  }))
  /** Shortcuts that work on particular pages (Help & support lists them too). */
  const pages = computed(() => [
    {
      key: 'lists',
      title: t('shortcuts.lists'),
      items: [
        { label: t('shortcuts.searchList'), keys: ['/'] },
        { label: t('shortcuts.nextItem'), keys: ['j'] },
        { label: t('shortcuts.previousItem'), keys: ['k'] },
        { label: t('shortcuts.openItem'), keys: ['enter'] },
      ] as ShortcutItem[],
    },
    {
      key: 'builder',
      title: t('shortcuts.builder'),
      items: [
        { label: t('builder.undo'), keys: ['meta', 'z'] },
        { label: t('builder.redo'), keys: ['meta', 'shift', 'z'] },
        { label: t('shortcuts.duplicate'), keys: ['meta', 'd'] },
        { label: t('shortcuts.removeField'), keys: ['delete'] },
        { label: t('shortcuts.moveUp'), keys: ['alt', 'arrowup'] },
        { label: t('shortcuts.moveDown'), keys: ['alt', 'arrowdown'] },
        { label: t('builder.fullscreen.enter'), keys: ['meta', 'shift', 'f'] },
      ] as ShortcutItem[],
    },
    {
      key: 'editing',
      title: t('shortcuts.editing'),
      items: [
        { label: t('shortcuts.save'), keys: ['meta', 's'] },
        { label: t('shortcuts.generate'), keys: ['meta', 'enter'] },
      ] as ShortcutItem[],
    },
  ])

  return { general, navigation, pages }
}

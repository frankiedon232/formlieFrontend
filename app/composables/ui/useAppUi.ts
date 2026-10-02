/** Shell-level UI state shared by sidebar, navbar, search and shortcuts (no secrets here). */
export function useAppUi() {
  const shortcutsOpen = useState('app:shortcuts-open', () => false)
  const notificationsOpen = useState('app:notifications-open', () => false)

  return { shortcutsOpen, notificationsOpen }
}

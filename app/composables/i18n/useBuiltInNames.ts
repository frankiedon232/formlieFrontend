/**
 * Names Formalie itself provides, shown in the viewer's language (owner, 2026-10-10: "what users type,
 * leave it as typed"): the built-in roles (while a workspace hasn't renamed them) and Formalie's default
 * lists (author `system`). Anything a workspace typed is returned as it is.
 */
import { BUILT_IN_ROLE_TEXT } from '#shared/utils/auth/permissions'

type BuiltIn = keyof typeof BUILT_IN_ROLE_TEXT
const isBuiltIn = (id: string | null | undefined): id is BuiltIn => !!id && id in BUILT_IN_ROLE_TEXT

export function useBuiltInNames() {
  const { t, te } = useI18n()

  /** A role's name: translated for Owner, Admin and Member while their name is still Formalie's. */
  const roleName = (id: string | null | undefined, name: string | null | undefined) =>
    isBuiltIn(id) && (!name || name === BUILT_IN_ROLE_TEXT[id].name) ? t(`access.builtInRole.${id}.name`) : (name ?? '')
  const roleDescription = (id: string | null | undefined, description: string | null | undefined) =>
    isBuiltIn(id) && (!description || description === BUILT_IN_ROLE_TEXT[id].description) ? t(`access.builtInRole.${id}.description`) : (description ?? '')

  // Formalie's default lists have fixed ids and can't be renamed in a workspace (use-only), so the id is enough
  /** A list's name and description: translated for Formalie's default lists. */
  const listName = (item: { id: string; name: string }) => (te(`library.defaultList.${item.id}.name`) ? t(`library.defaultList.${item.id}.name`) : item.name)
  const listDescription = (item: { id: string; description?: string | null }) =>
    te(`library.defaultList.${item.id}.description`) ? t(`library.defaultList.${item.id}.description`) : (item.description ?? '')
  /** A level of a default list (Country, Region, City). */
  const levelLabel = (item: { id: string }, level: { key: string; label: string }) =>
    te(`library.defaultList.${item.id}.name`) && te(`library.defaultLevel.${level.key}`) ? t(`library.defaultLevel.${level.key}`) : level.label

  return { roleName, roleDescription, listName, listDescription, levelLabel }
}

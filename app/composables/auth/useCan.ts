/**
 * Roles & access in the app (F22): what the signed-in person's role allows (from the session). The
 * server checks every call anyway; the app uses this to show only what the role can use (menus, rail
 * areas, pages, buttons). Owners can do everything.
 */
import type { Permission } from '#shared/utils/auth/permissions'

/** Pages and the permission each needs (first match), mirrored from the server's table. */
const PAGE_PERMISSIONS: [RegExp, Permission][] = [
  [/^\/forms\/new(\/|$)/, 'forms.create'],
  [/^\/forms\/[^/]+\/(build|design|logic|share|versions)(\/|$)/, 'forms.edit'],
  [/^\/forms\/[^/]+\/storage(\/|$)/, 'data.view'],
  [/^\/people\/roles\/[^/]+$/, 'people.view'],
  [/^\/people(\/|$)/, 'people.view'],
  [/^\/audit(\/|$)/, 'audit.view'],
  [/^\/data-sources(\/|$)/, 'data.view'],
  [/^\/api-service(\/|$)/, 'api.view'],
  [/^\/analytics(\/|$)/, 'analytics.view'],
  [/^\/ai(\/|$)/, 'ai.use'],
  [/^\/(responses|forms\/[^/]+\/responses)(\/|$)/, 'responses.view'],
]
export const pagePermission = (path: string) => PAGE_PERMISSIONS.find(([pattern]) => pattern.test(path))?.[1] ?? null

export function useCan() {
  const session = useSession()
  const granted = computed(() => new Set(session.user.value?.permissions ?? []))
  /** True when the role allows it (owners always; before the session knows, nothing). */
  const can = (permission: Permission) => session.user.value?.role === 'owner' || granted.value.has(permission)
  return { can }
}

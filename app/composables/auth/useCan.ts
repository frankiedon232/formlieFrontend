/**
 * Roles & access in the app (F22): what the signed-in person's role allows (from the session). The
 * server checks every call anyway; the app uses this to show only what the role can use (menus, rail
 * areas, pages, buttons). Owners can do everything.
 */
import type { Permission, Scope } from '#shared/utils/auth/permissions'

/** Pages and the permission each needs (first match), mirrored from the server's table. */
const PAGE_PERMISSIONS: [RegExp, Permission][] = [
  [/^\/forms\/new(\/|$)/, 'forms.create'],
  // The libraries (F22 R2 M3): their pages need "see"; each item then says what may change (its `can`)
  [/^\/settings\/themes\/new$/, 'themes.create'],
  [/^\/settings\/landing-pages\/new$/, 'pages.create'],
  [/^\/templates(\/|$)/, 'templates.view'],
  [/^\/option-sets(\/|$)/, 'lists.view'],
  [/^\/settings\/themes(\/|$)/, 'themes.view'],
  [/^\/settings\/landing-pages(\/|$)/, 'pages.view'],
  [/^\/forms\/trash(\/|$)/, 'forms.delete'],
  // The role must reach at least some forms for each tab; the form itself then decides (its `can`)
  [/^\/forms\/[^/]+\/(build|design|logic)(\/|$)/, 'forms.edit'],
  [/^\/forms\/[^/]+\/share(\/|$)/, 'forms.share_view'],
  [/^\/forms\/[^/]+\/versions(\/|$)/, 'forms.versions'],
  [/^\/forms\/[^/]+\/preview(\/|$)/, 'forms.preview'],
  [/^\/forms\/[^/]+\/storage(\/|$)/, 'data.storage'],
  [/^\/people\/roles\/[^/]+$/, 'people.view'],
  [/^\/people(\/|$)/, 'people.view'],
  [/^\/audit(\/|$)/, 'audit.view'],
  [/^\/data-sources\/connections\/new$/, 'data.create'],
  [/^\/data-sources\/connections\/[^/]+\/edit$/, 'data.view'],
  [/^\/data-sources\/explorer(\/|$)/, 'data.browse'],
  [/^\/data-sources\/query(\/|$)/, 'data.query'],
  [/^\/data-sources\/(activity|transfers)(\/|$)/, 'audit.view'],
  [/^\/data-sources(\/|$)/, 'data.view'],
  [/^\/api-service\/endpoints\/(new|[^/]+\/edit)$/, 'api.endpoints'],
  [/^\/api-service(\/|$)/, 'api.view'],
  [/^\/analytics(\/|$)/, 'analytics.view'],
  [/^\/ai\/(create-form|templates)(\/|$)/, 'ai.create'],
  [/^\/ai\/(analysis|insights)(\/|$)/, 'ai.analyse'],
  [/^\/ai\/translate(\/|$)/, 'ai.translate'],
  [/^\/ai\/history(\/|$)/, 'ai.history'],
  [/^\/ai\/settings(\/|$)/, 'ai.settings'],
  [/^\/ai(\/|$)/, 'ai.use'],
  [/^\/(responses|forms\/[^/]+\/responses)(\/|$)/, 'responses.view'],
]
export const pagePermission = (path: string) => PAGE_PERMISSIONS.find(([pattern]) => pattern.test(path))?.[1] ?? null

export function useCan() {
  const session = useSession()
  const granted = computed(() => new Set(session.user.value?.permissions ?? []))
  /** True when the role allows it (owners always; before the session knows, nothing). */
  const can = (permission: Permission) => session.user.value?.role === 'owner' || granted.value.has(permission)
  /** How far it reaches (own · shared · all), or null. Per-item answers come from the server (`can` on forms, folders …). */
  const scope = (permission: Permission): Scope | null => (session.user.value?.role === 'owner' ? 'all' : (session.user.value?.grants?.[permission] ?? null))
  return { can, scope }
}

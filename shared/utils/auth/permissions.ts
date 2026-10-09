/**
 * Roles & access (F22, brought forward into F16 by the owner, 2026-10-09): what a role may do, per area
 * of the platform. Each workspace keeps its own roles (Owner is built in with everything and can't be
 * changed, so a workspace never locks itself out); a person holds one role. The server checks every call
 * against `permissionFor` (by address and action) and the app hides what the role can't use.
 */

export const PERMISSION_AREAS = [
  { key: 'forms', actions: ['view', 'create', 'edit', 'publish', 'delete', 'all'] },
  // review = status, tags and notes; edit = correct submitted answers (owner, 2026-10-09)
  { key: 'responses', actions: ['view', 'review', 'edit', 'delete', 'export'] },
  { key: 'resources', actions: ['manage'] },
  { key: 'analytics', actions: ['view'] },
  { key: 'data', actions: ['view', 'query', 'manage'] },
  { key: 'api', actions: ['view', 'manage'] },
  { key: 'people', actions: ['view', 'manage', 'approve'] },
  { key: 'roles', actions: ['manage'] },
  { key: 'settings', actions: ['view', 'manage'] },
  { key: 'audit', actions: ['view', 'export'] },
  { key: 'ai', actions: ['use'] },
] as const

export type PermissionArea = (typeof PERMISSION_AREAS)[number]['key']
export type Permission = { [A in (typeof PERMISSION_AREAS)[number] as A['key']]: `${A['key']}.${A['actions'][number]}` }[PermissionArea]
export const ALL_PERMISSIONS = PERMISSION_AREAS.flatMap(area => area.actions.map(action => `${area.key}.${action}`)) as Permission[]

/** Ids of the roles every workspace starts with. */
export const OWNER_ROLE = 'owner'
export const BUILT_IN_ROLES = ['owner', 'admin', 'member'] as const

/** What the built-in roles start with (Admin and Member can be changed by owners; Owner can't). */
export const DEFAULT_ROLE_PERMISSIONS: Record<(typeof BUILT_IN_ROLES)[number], Permission[]> = {
  owner: ALL_PERMISSIONS,
  admin: ALL_PERMISSIONS.filter(item => item !== 'roles.manage'),
  member: ['forms.view', 'forms.create', 'forms.edit', 'forms.publish', 'responses.view', 'responses.review', 'responses.edit', 'responses.export', 'analytics.view', 'ai.use'],
}

/** Some permissions only make sense with another (editing needs viewing …): ticking one ticks these too. */
export const PERMISSION_NEEDS: Partial<Record<Permission, Permission[]>> = {
  'forms.create': ['forms.view'],
  'forms.edit': ['forms.view'],
  'forms.publish': ['forms.view', 'forms.edit'],
  'forms.delete': ['forms.view'],
  'forms.all': ['forms.view'],
  'responses.review': ['responses.view'],
  'responses.edit': ['responses.view'],
  'responses.delete': ['responses.view'],
  'responses.export': ['responses.view'],
  'data.query': ['data.view'],
  'data.manage': ['data.view'],
  'api.manage': ['api.view'],
  'people.manage': ['people.view'],
  'people.approve': ['people.view'],
  'roles.manage': ['people.view'],
  'settings.manage': ['settings.view'],
  'audit.export': ['audit.view'],
}
/** A set of permissions with everything they need added. */
export function withNeeds(list: readonly string[]): Permission[] {
  const out = new Set(list.filter((item): item is Permission => (ALL_PERMISSIONS as string[]).includes(item)))
  for (let changed = true; changed; ) {
    changed = false
    for (const item of [...out])
      for (const need of PERMISSION_NEEDS[item] ?? [])
        if (!out.has(need)) {
          out.add(need)
          changed = true
        }
  }
  return ALL_PERMISSIONS.filter(item => out.has(item))
}

/**
 * The permission an API call needs (method + path without /api/v1), or null for calls every signed-in
 * person may make (their own profile, menus, notifications, lists the builder reads, workspace settings
 * pages read). First match wins.
 */
export function permissionFor(method: string, path: string): Permission | null {
  const m = method.toUpperCase()
  const read = m === 'GET'
  const p = path.split('?')[0]!
  const rules: [RegExp, Permission | null | ((read: boolean) => Permission | null)][] = [
    [/^\/(me|navigation|notifications|directory|auth|public|crypto|tenants|health|uploads|storage|files|downloads|response-files|response-exports|explorer-exports\/[^/]+$)(\/|$)/, null],
    // People and roles
    [/^\/roles(\/|$)/, r => (r ? 'people.view' : 'roles.manage')],
    [/^\/people\/[^/]+\/(approve|reject)$/, 'people.approve'],
    [/^\/people(\/|$)/, r => (r ? 'people.view' : 'people.manage')],
    [/^\/org(\/|$)/, r => (r ? null : 'people.manage')],
    // Forms and responses
    [/^\/forms\/[^/]+\/responses\/export$/, 'responses.export'],
    [/^\/forms\/[^/]+\/responses(\/|$)/, 'responses.view'],
    [/^\/responses\/exports(\/|$)/, 'responses.export'],
    // Opening a file is reading (a short private link); changing answers is checked again in the route (Edit)
    [/^\/responses\/[^/]+\/files$/, 'responses.view'],
    [/^\/responses\/[^/]+$/, () => (m === 'DELETE' ? 'responses.delete' : read ? 'responses.view' : 'responses.review')],
    [/^\/responses(\/|$)/, r => (r ? 'responses.view' : 'responses.review')],
    [/^\/forms\/[^/]+\/publish$/, 'forms.publish'],
    [/^\/forms\/(import|[^/]+\/duplicate)$/, 'forms.create'],
    [/^\/forms\/trash$/, 'forms.delete'],
    [/^\/forms$/, r => (r ? 'forms.view' : 'forms.create')],
    [/^\/forms\/[^/]+$/, () => (m === 'DELETE' ? 'forms.delete' : read ? 'forms.view' : 'forms.edit')],
    [/^\/forms(\/|$)/, r => (r ? 'forms.view' : 'forms.edit')],
    // Templates, themes, landing pages, lists, saved fields, folders: everyone reads them; changes need resources.manage
    [/^\/(templates|themes|page-designs|option-lists|field-library|folders)(\/|$)/, r => (r || /\/translate-content$/.test(p) ? null : 'resources.manage')],
    [/^\/analytics(\/|$)/, 'analytics.view'],
    // Data sources
    [/^\/datasources\/[^/]+\/(query|explorer\/exports)/, 'data.query'],
    [/^\/(datasources|destinations|saved-queries|datasource-exports|explorer-exports)(\/|$)/, r => (r ? 'data.view' : 'data.manage')],
    // API service and webhooks
    [/^\/(api-[a-z-]+|webhooks|webhook-deliveries)(\/|$)/, r => (r ? 'api.view' : 'api.manage')],
    // Audit trail
    [/^\/audit-logs\/export/, 'audit.export'],
    [/^\/audit-logs(\/|$)/, 'audit.view'],
    // Settings: pages read them (appearance, language, defaults); security and sent emails need settings.view
    [/^\/settings\/(security|emails)(\/|$)/, r => (r ? 'settings.view' : 'settings.manage')],
    [/^\/(settings|privacy|onboarding)(\/|$)/, r => (r ? null : 'settings.manage')],
  ]
  for (const [pattern, rule] of rules) if (pattern.test(p)) return typeof rule === 'function' ? rule(read) : rule
  return null
}

/**
 * Roles & access (F22, brought forward into F16 by the owner, 2026-10-09; granular with scope, R2,
 * 2026-10-10): what a role may do, action by action, per area of the platform. Each workspace keeps its
 * own roles (Owner is built in with everything and can't be changed, so a workspace never locks itself
 * out); a person holds one role. The server checks every call (by address, then each action against the
 * item: who made it, whom it is shared with, which folder it sits in) and the app hides what the role
 * can't use, everywhere the action appears.
 *
 * A grant has a scope (owner: "no matter the permission granted, I can be limited to even what I created";
 * 2026-10-10: "None, Own, Shared, Own & Shared, All"):
 *   own         only on what the person made (leaving the action out means not even their own)
 *   shared      only on forms others shared with them (form sharing never goes beyond the role)
 *   own_shared  both
 *   all         everything in the workspace
 * Actions without a scope are on / off (stored as `all`). A scope is a set of parts: what they made,
 * what is shared with them, everything else (bits 1, 2, 4).
 */

export type Scope = 'own' | 'shared' | 'own_shared' | 'all'
export const SCOPES: readonly Scope[] = ['own', 'shared', 'own_shared', 'all']
const PARTS: Record<Scope, number> = { own: 1, shared: 2, own_shared: 3, all: 7 }
/** The parts a scope covers: own (1) · shared with them (2) · everything else (4). */
export const scopeParts = (scope: Scope) => PARTS[scope]
const FORM: readonly Scope[] = ['own', 'shared', 'own_shared', 'all']
const OWNED: readonly Scope[] = ['own', 'all']

interface ActionDef {
  readonly key: string
  readonly scopes?: readonly Scope[]
}
interface GroupDef {
  readonly key: string
  readonly actions: readonly ActionDef[]
}

/** The catalogue: area → group (for the editor) → action. New actions are added here only. */
export const PERMISSION_AREAS = [
  {
    key: 'forms',
    groups: [
      { key: 'see', actions: [{ key: 'view', scopes: FORM }, { key: 'preview', scopes: FORM }] },
      { key: 'create', actions: [{ key: 'create' }, { key: 'import' }, { key: 'duplicate', scopes: FORM }, { key: 'save_template', scopes: FORM }] },
      { key: 'build', actions: [{ key: 'rename', scopes: FORM }, { key: 'edit', scopes: FORM }, { key: 'versions', scopes: FORM }] },
      { key: 'share', actions: [{ key: 'share_view', scopes: FORM }, { key: 'share', scopes: FORM }, { key: 'availability', scopes: FORM }] },
      {
        key: 'lifecycle',
        actions: [
          { key: 'publish', scopes: FORM },
          { key: 'close', scopes: FORM },
          { key: 'archive', scopes: FORM },
          { key: 'move', scopes: FORM },
          { key: 'delete', scopes: FORM },
          { key: 'purge', scopes: FORM },
        ],
      },
    ],
  },
  { key: 'folders', groups: [{ key: 'folders', actions: [{ key: 'create' }, { key: 'edit', scopes: OWNED }, { key: 'delete', scopes: OWNED }, { key: 'access' }] }] },
  // review = status, tags and notes; edit = correct submitted answers (owner, 2026-10-09). Scope (F22 R2 M2):
  // own = responses to forms they made, shared = also forms shared with them, all = every form's responses
  {
    key: 'responses',
    groups: [{ key: 'responses', actions: [{ key: 'view', scopes: FORM }, { key: 'review', scopes: FORM }, { key: 'edit', scopes: FORM }, { key: 'delete', scopes: FORM }, { key: 'export', scopes: FORM }] }],
  },
  // Workspace resources (F22 R2 M3): seeing a library page, making, changing (own · all), copying, deleting (own · all).
  // Formalie's built-in items are use-only for everyone. Templates are made from a form (forms.save_template).
  { key: 'templates', groups: [{ key: 'templates', actions: [{ key: 'view' }, { key: 'edit', scopes: OWNED }, { key: 'duplicate' }, { key: 'delete', scopes: OWNED }] }] },
  { key: 'lists', groups: [{ key: 'lists', actions: [{ key: 'view' }, { key: 'create' }, { key: 'edit', scopes: OWNED }, { key: 'duplicate' }, { key: 'delete', scopes: OWNED }] }] },
  { key: 'themes', groups: [{ key: 'themes', actions: [{ key: 'view' }, { key: 'create' }, { key: 'edit', scopes: OWNED }, { key: 'duplicate' }, { key: 'delete', scopes: OWNED }] }] },
  { key: 'pages', groups: [{ key: 'pages', actions: [{ key: 'view' }, { key: 'create' }, { key: 'edit', scopes: OWNED }, { key: 'duplicate' }, { key: 'delete', scopes: OWNED }] }] },
  { key: 'fields', groups: [{ key: 'fields', actions: [{ key: 'view' }, { key: 'create' }, { key: 'delete', scopes: OWNED }] }] },
  { key: 'analytics', groups: [{ key: 'analytics', actions: [{ key: 'view' }] }] },
  // Data sources (F22 R2 M4): connections, the explorer, queries and where forms keep their responses
  {
    key: 'data',
    groups: [
      { key: 'connections', actions: [{ key: 'view' }, { key: 'create' }, { key: 'edit', scopes: OWNED }, { key: 'delete', scopes: OWNED }] },
      { key: 'explorer', actions: [{ key: 'browse' }, { key: 'rows' }, { key: 'structure' }, { key: 'export' }] },
      { key: 'query', actions: [{ key: 'query' }, { key: 'query_write' }, { key: 'saved' }] },
      { key: 'storage', actions: [{ key: 'storage' }] },
    ],
  },
  // API service (F22 R2 M4)
  {
    key: 'api',
    groups: [
      { key: 'services', actions: [{ key: 'view' }, { key: 'service_create' }, { key: 'service_edit', scopes: OWNED }, { key: 'service_delete', scopes: OWNED }, { key: 'endpoints' }, { key: 'try' }] },
      { key: 'security', actions: [{ key: 'tokens' }, { key: 'key' }, { key: 'access' }, { key: 'logs' }] },
      { key: 'webhooks', actions: [{ key: 'webhooks' }] },
    ],
  },
  { key: 'people', groups: [{ key: 'people', actions: [{ key: 'view' }, { key: 'manage' }, { key: 'approve' }] }] },
  { key: 'roles', groups: [{ key: 'roles', actions: [{ key: 'manage' }] }] },
  { key: 'settings', groups: [{ key: 'settings', actions: [{ key: 'view' }, { key: 'manage' }] }] },
  { key: 'audit', groups: [{ key: 'audit', actions: [{ key: 'view' }, { key: 'export' }] }] },
  // AI assistant (F22 R2 M4): using it at all, then each part of it
  { key: 'ai', groups: [{ key: 'ai', actions: [{ key: 'use' }, { key: 'create' }, { key: 'assist' }, { key: 'analyse' }, { key: 'translate' }, { key: 'history' }, { key: 'settings' }] }] },
] as const satisfies readonly { key: string; groups: readonly GroupDef[] }[]

type Area = (typeof PERMISSION_AREAS)[number]
export type PermissionArea = Area['key']
export type Permission = { [A in Area as A['key']]: `${A['key']}.${A['groups'][number]['actions'][number]['key']}` }[PermissionArea]
/** What a role holds: each permission it has, with its scope. */
export type Grants = Partial<Record<Permission, Scope>>

export const ALL_PERMISSIONS = PERMISSION_AREAS.flatMap(area => area.groups.flatMap(group => group.actions.map(action => `${area.key}.${action.key}`))) as Permission[]
const DEFS = new Map<string, readonly Scope[] | undefined>(
  PERMISSION_AREAS.flatMap(area => area.groups.flatMap(group => group.actions.map(action => [`${area.key}.${action.key}`, (action as ActionDef).scopes] as const))),
)
/** The scopes an action offers (none = on / off). */
export const scopesOf = (permission: string): readonly Scope[] | undefined => DEFS.get(permission)
export const isPermission = (value: string): value is Permission => DEFS.has(value)

/** Ids of the roles every workspace starts with. */
export const OWNER_ROLE = 'owner'
export const BUILT_IN_ROLES = ['owner', 'admin', 'member'] as const

/** The built-in roles' names and descriptions as Formalie ships them (English); the app shows them translated while unchanged. */
export const BUILT_IN_ROLE_TEXT = {
  owner: { name: 'Owner', description: "Everything, including roles and the workspace itself. It can't be changed." },
  admin: { name: 'Admin', description: 'Manages people, forms, data, the API service and settings.' },
  member: { name: 'Member', description: 'Builds and publishes forms and works with their responses.' },
} as const

/** Everything, everywhere. */
export const ALL_GRANTS = Object.fromEntries(ALL_PERMISSIONS.map(item => [item, 'all'])) as Grants
const grant = (list: Permission[], scope: Scope = 'all') => Object.fromEntries(list.map(item => [item, scopesOf(item) ? scope : 'all'])) as Grants

/** What the built-in roles start with (Admin and Member can be changed by owners; Owner can't). */
export const DEFAULT_ROLE_GRANTS: Record<(typeof BUILT_IN_ROLES)[number], Grants> = {
  owner: ALL_GRANTS,
  admin: grant(ALL_PERMISSIONS.filter(item => item !== 'roles.manage')),
  member: {
    ...grant(['forms.view', 'forms.preview', 'forms.duplicate', 'forms.save_template', 'forms.rename', 'forms.edit', 'forms.versions', 'forms.share_view', 'forms.share', 'forms.availability', 'forms.publish', 'forms.close', 'forms.archive', 'forms.move'], 'own_shared'),
    ...grant(['forms.create', 'forms.import', 'folders.create']),
    ...grant(['folders.edit', 'folders.delete'], 'own'),
    ...grant(['responses.view', 'responses.review', 'responses.edit', 'responses.export'], 'own_shared'),
    ...grant(['analytics.view', 'ai.use', 'ai.create', 'ai.assist', 'ai.analyse', 'ai.translate', 'ai.history', 'templates.view', 'lists.view', 'themes.view', 'pages.view', 'fields.view']),
  },
}

/** Some actions only make sense with another (changing needs seeing …): granting one grants these too, as far as it reaches. */
export const PERMISSION_NEEDS: Partial<Record<Permission, Permission[]>> = {
  'forms.preview': ['forms.view'],
  'forms.duplicate': ['forms.view', 'forms.create'],
  'forms.save_template': ['forms.view'],
  'forms.rename': ['forms.view'],
  'forms.edit': ['forms.view'],
  'forms.versions': ['forms.view', 'forms.edit'],
  'forms.share_view': ['forms.view'],
  'forms.share': ['forms.share_view'],
  'forms.availability': ['forms.view'],
  'forms.publish': ['forms.view'],
  'forms.close': ['forms.view'],
  'forms.archive': ['forms.view'],
  'forms.move': ['forms.view'],
  'forms.delete': ['forms.view'],
  'forms.purge': ['forms.delete'],
  'responses.review': ['responses.view'],
  'responses.edit': ['responses.view'],
  'responses.delete': ['responses.view'],
  'responses.export': ['responses.view'],
  'data.create': ['data.view'],
  'data.edit': ['data.view'],
  'data.delete': ['data.view'],
  'data.browse': ['data.view'],
  'data.rows': ['data.browse'],
  'data.structure': ['data.browse'],
  'data.export': ['data.browse'],
  'data.query': ['data.view'],
  'data.query_write': ['data.query'],
  'data.saved': ['data.query'],
  'data.storage': ['data.view'],
  'api.service_create': ['api.view'],
  'api.service_edit': ['api.view'],
  'api.service_delete': ['api.view'],
  'api.endpoints': ['api.view'],
  'api.try': ['api.view'],
  'api.tokens': ['api.view'],
  'api.key': ['api.view'],
  'api.access': ['api.view'],
  'api.logs': ['api.view'],
  'api.webhooks': ['api.view'],
  'ai.create': ['ai.use'],
  'ai.assist': ['ai.use'],
  'ai.analyse': ['ai.use'],
  'ai.translate': ['ai.use'],
  'ai.history': ['ai.use'],
  'ai.settings': ['ai.use'],
  'people.manage': ['people.view'],
  'people.approve': ['people.view'],
  'roles.manage': ['people.view'],
  'settings.manage': ['settings.view'],
  'audit.export': ['audit.view'],
}

const bits = (mask: number) => (mask & 1) + ((mask >> 1) & 1) + ((mask >> 2) & 1)
/** The narrowest scope an action offers that covers all these parts (what something it needs must reach). */
function cover(permission: Permission, mask: number): Scope {
  const offered = scopesOf(permission)
  if (!offered) return 'all'
  return offered.filter(item => (PARTS[item] & mask) === mask).sort((a, b) => bits(PARTS[a]) - bits(PARTS[b]))[0] ?? 'all'
}
/** The widest scope an action offers inside these parts (an action held back to what it needs), or null. */
function within(permission: Permission, mask: number): Scope | null {
  const offered = scopesOf(permission)
  if (!offered) return mask === 7 ? 'all' : null
  return offered.filter(item => (PARTS[item] & ~mask) === 0).sort((a, b) => bits(PARTS[b]) - bits(PARTS[a]))[0] ?? null
}
/** A scope as the action offers it: one it doesn't offer becomes the widest inside it, else the narrowest it has (never wider). */
function fit(permission: Permission, scope: Scope): Scope {
  const offered = scopesOf(permission)
  if (!offered) return 'all'
  return within(permission, PARTS[scope]) ?? [...offered].sort((x, y) => bits(PARTS[x]) - bits(PARTS[y]))[0]!
}

/** Grants cleaned up (unknown actions dropped, scopes fitted), with what they need added as far as they reach. */
export function withNeeds(input: Readonly<Record<string, string | undefined>>): Grants {
  const out: Grants = {}
  for (const [key, value] of Object.entries(input)) if (isPermission(key) && value && value in PARTS) out[key] = fit(key, value as Scope)
  for (let changed = true; changed; ) {
    changed = false
    for (const [item, scope] of Object.entries(out) as [Permission, Scope][])
      for (const need of PERMISSION_NEEDS[item] ?? []) {
        // What it needs must reach at least the same parts (both together when it had others already)
        const has = out[need]
        const wanted = cover(need, (has ? PARTS[has] : 0) | PARTS[scope])
        if (wanted !== has) {
          out[need] = wanted
          changed = true
        }
      }
  }
  return Object.fromEntries(ALL_PERMISSIONS.filter(item => out[item]).map(item => [item, out[item]])) as Grants
}

/** Every action that needs this one, directly or through another. */
export function dependentsOf(permission: Permission): Permission[] {
  const out = new Set<Permission>()
  for (let changed = true; changed; ) {
    changed = false
    for (const [item, needs] of Object.entries(PERMISSION_NEEDS) as [Permission, Permission[]][])
      if (!out.has(item) && needs.some(need => need === permission || out.has(need))) {
        out.add(item)
        changed = true
      }
  }
  return [...out]
}

/**
 * One action changed in a role (the editor): what needs it follows, removed with it or held back to the
 * parts it still reaches (edit can't reach what view doesn't); what it needs is added.
 */
export function setGrant(grants: Grants, permission: Permission, scope: Scope | null): Grants {
  const dependents = new Set(dependentsOf(permission))
  const next: Grants = { ...grants }
  if (scope) next[permission] = fit(permission, scope)
  const reach = scope ? PARTS[next[permission]!] : 0
  for (const item of [permission, ...dependents]) {
    const has = next[item]
    if (!has || (item === permission && scope)) continue
    const kept = within(item, PARTS[has] & reach)
    if (kept) next[item] = kept
    else next[item] = undefined
  }
  return withNeeds(Object.fromEntries(Object.entries(next).filter(([, value]) => value)) as Grants)
}

/** How much of the platform a role opens (0–1): each action weighed by its reach (each part a third, all whole). */
export const reachOf = (grants: Grants) => Object.values(withNeeds(grants)).reduce((sum, scope) => sum + bits(PARTS[scope!]) / 3, 0) / ALL_PERMISSIONS.length
/** The areas a role opens at least one action in. */
export const areasOf = (grants: Grants) => PERMISSION_AREAS.filter(area => area.groups.some(group => group.actions.some(action => grants[`${area.key}.${action.key}` as Permission]))).length

/** What the coarse data / API / AI permissions became (F22 R2 M4), each at all: the same effect. */
export const SPLIT_PERMISSIONS: Record<string, string[]> = {
  'data.view': ['data.view', 'data.browse'],
  'data.query': ['data.query', 'data.query_write', 'data.export', 'data.saved'],
  'data.manage': ['data.create', 'data.edit', 'data.delete', 'data.rows', 'data.structure', 'data.storage', 'data.saved'],
  'api.view': ['api.view'],
  'api.manage': ['api.service_create', 'api.service_edit', 'api.service_delete', 'api.endpoints', 'api.try', 'api.tokens', 'api.key', 'api.access', 'api.logs', 'api.webhooks'],
  'ai.use': ['ai.use', 'ai.create', 'ai.assist', 'ai.analyse', 'ai.translate', 'ai.history'],
}

/** A role saved before scopes (a list of permissions) as grants with the same effect (2026-10-10). */
export function grantsFromList(list: readonly string[]): Grants {
  const has = (item: string) => list.includes(item)
  // Without "every form" a person worked on their own forms and those shared with them
  const forms: Scope = has('forms.all') ? 'all' : 'own_shared'
  const out: Record<string, Scope> = {}
  const give = (items: string[], scope: Scope) => items.forEach(item => (out[item] = scope))
  if (has('forms.view')) give(['forms.view', 'forms.preview', 'forms.share_view'], forms)
  if (has('forms.create')) give(['forms.create', 'forms.import'], 'all')
  if (has('forms.create')) give(['forms.duplicate'], forms)
  if (has('forms.edit')) give(['forms.rename', 'forms.edit', 'forms.versions', 'forms.share', 'forms.availability', 'forms.close', 'forms.archive', 'forms.move', 'forms.save_template'], forms)
  if (has('forms.publish')) give(['forms.publish'], forms)
  if (has('forms.delete')) give(['forms.delete', 'forms.purge'], forms)
  // Folders and the libraries were "resources"; deciding who sees a folder goes with managing settings
  if (has('resources.manage')) give(['folders.create', 'folders.edit', 'folders.delete', ...RESOURCE_CHANGES], 'all')
  give(RESOURCE_VIEWS, 'all')
  if (has('settings.manage')) give(['folders.access'], 'all')
  for (const item of list) if (isPermission(item) && !item.startsWith('forms.') && !item.startsWith('folders.')) out[item] = item.startsWith('responses.') ? forms : 'all'
  for (const item of list) for (const part of SPLIT_PERMISSIONS[item] ?? []) out[part] = 'all'
  return withNeeds(out)
}

/** Every library's "see" permission (granted to every role by default) and its changes (once "resources.manage"). */
export const RESOURCE_VIEWS = ['templates.view', 'lists.view', 'themes.view', 'pages.view', 'fields.view']
export const RESOURCE_CHANGES = ['templates.edit', 'templates.duplicate', 'templates.delete', 'lists.create', 'lists.edit', 'lists.duplicate', 'lists.delete', 'themes.create', 'themes.edit', 'themes.duplicate', 'themes.delete', 'pages.create', 'pages.edit', 'pages.duplicate', 'pages.delete', 'fields.create', 'fields.delete']

/** Address rules for a library: reads are open, then create · duplicate · change · delete (the route checks own · all). */
function resourceRules(base: string, area: 'templates' | 'lists' | 'themes' | 'pages' | 'fields', method: string): [RegExp, Permission | null][] {
  const p = (action: string) => `${area}.${action}` as Permission
  const read = method === 'GET'
  return [
    [new RegExp(`^/${base}/[^/]+/duplicate$`), read ? null : p('duplicate')],
    [new RegExp(`^/${base}$`), read ? null : p('create')],
    [new RegExp(`^/${base}/[^/]+$`), read ? null : method === 'DELETE' ? p('delete') : p('edit')],
    [new RegExp(`^/${base}(/|$)`), read ? null : p('edit')],
  ]
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
    [/^\/(me|navigation|notifications|directory|auth|public|crypto|tenants|health|uploads|storage|files|downloads|response-files|response-exports|datasource-exports)(\/|$)/, null],
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
    // Forms (F22 R2): the address says "works with forms"; each route then checks its own action on the form
    // (rename, move, publish …) with the role's scope, the sharing and the folder.
    [/^\/forms\/pass$/, null],
    [/^\/forms\/import$/, 'forms.import'],
    [/^\/forms\/[^/]+\/duplicate$/, 'forms.duplicate'],
    [/^\/forms\/[^/]+\/publish$/, 'forms.publish'],
    [/^\/forms\/trash$/, 'forms.purge'],
    [/^\/forms$/, r => (r ? 'forms.view' : 'forms.create')],
    [/^\/forms(\/|$)/, 'forms.view'],
    // Folders: creating, changing (own · all), deleting (own · all), deciding who sees them; everyone reads the ones they may see
    [/^\/folders\/[^/]+\/access$/, 'folders.access'],
    [/^\/folders$/, r => (r ? null : 'folders.create')],
    [/^\/folders\/[^/]+$/, () => (read ? null : m === 'DELETE' ? 'folders.delete' : 'folders.edit')],
    [/^\/folders(\/|$)/, null],
    // Templates, lists, themes, landing pages, saved fields (F22 R2 M3): everyone reads them (forms use them);
    // each change has its own permission, and the route checks own · all on the item
    [/^\/templates\/translate-content$/, null],
    [/^\/templates$/, r => (r ? null : 'forms.save_template')],
    [/^\/templates\/[^/]+\/sync$/, 'templates.edit'],
    ...resourceRules('templates', 'templates', m),
    ...resourceRules('option-lists', 'lists', m),
    ...resourceRules('themes', 'themes', m),
    ...resourceRules('page-designs', 'pages', m),
    ...resourceRules('field-library', 'fields', m),
    [/^\/analytics(\/|$)/, 'analytics.view'],
    // Data sources
    // Data sources (F22 R2 M4): each part its own permission; changing or deleting a connection is own · all (checked in the route)
    [/^\/datasources\/[^/]+\/explorer\/rows$/, r => (r ? 'data.browse' : 'data.rows')],
    [/^\/datasources\/[^/]+\/explorer\/(tables|changes)$/, r => (r ? 'data.browse' : 'data.structure')],
    [/^\/datasources\/[^/]+\/explorer\/exports$/, 'data.export'],
    [/^\/datasources\/[^/]+\/explorer(\/|$)/, 'data.browse'],
    [/^\/explorer-exports(\/|$)/, 'data.export'],
    [/^\/datasources\/[^/]+\/query\/export$/, 'data.export'],
    // Running a changing statement also needs query_write (checked in the route, which knows the statement)
    [/^\/datasources\/[^/]+\/(query|query-history)$/, 'data.query'],
    [/^\/datasources\/test$/, 'data.view'],
    [/^\/datasources\/[^/]+\/test$/, 'data.edit'],
    [/^\/datasources\/[^/]+\/duplicate$/, 'data.create'],
    [/^\/datasources$/, r => (r ? 'data.view' : 'data.create')],
    [/^\/datasources\/[^/]+$/, () => (read ? 'data.view' : m === 'DELETE' ? 'data.delete' : 'data.edit')],
    [/^\/datasources(\/|$)/, 'data.view'],
    [/^\/saved-queries(\/|$)/, r => (r ? 'data.view' : 'data.saved')],
    [/^\/destinations(\/|$)/, r => (r ? 'data.view' : 'data.storage')],
    // API service and webhooks
    // API service (F22 R2 M4): reading needs api.view; each change its own permission (services own · all, checked in the route)
    [/^\/api-service\/key\/rotate$/, 'api.key'],
    [/^\/api-service\/limits$/, r => (r ? 'api.view' : 'api.access')],
    [/^\/api-access-rules\/test$/, 'api.view'],
    [/^\/api-access-rules(\/|$)/, r => (r ? 'api.view' : 'api.access')],
    [/^\/api-logs\/settings$/, r => (r ? 'api.view' : 'api.logs')],
    [/^\/api-services\/[^/]+\/duplicate$/, 'api.service_create'],
    [/^\/api-services$/, r => (r ? 'api.view' : 'api.service_create')],
    [/^\/api-services\/[^/]+$/, () => (read ? 'api.view' : m === 'DELETE' ? 'api.service_delete' : 'api.service_edit')],
    [/^\/api-endpoints\/[^/]+\/try$/, 'api.try'],
    [/^\/api-endpoints(\/|$)/, r => (r ? 'api.view' : 'api.endpoints')],
    [/^\/api-tokens(\/|$)/, r => (r ? 'api.view' : 'api.tokens')],
    [/^\/(webhooks|webhook-deliveries)(\/|$)/, r => (r ? 'api.view' : 'api.webhooks')],
    [/^\/api-[a-z-]+(\/|$)/, r => (r ? 'api.view' : 'api.service_edit')],
    // AI assistant (F19): reading the settings and usage is part of using it; each part checks its own permission
    [/^\/ai\/settings$/, r => (r ? 'ai.use' : 'ai.settings')],
    // Applying or discarding your own draft is part of using it (applying also checks forms / templates / themes create)
    [/^\/ai\/requests\/[^/]+\/(apply|discard)$/, 'ai.use'],
    [/^\/ai\/forms\/[^/]+\/assist$/, 'ai.assist'],
    [/^\/ai\/(analysis|digest|ask)$/, 'ai.analyse'],
    [/^\/ai\/responses\/[^/]+\/summary$/, 'ai.analyse'],
    [/^\/ai\/(forms|templates|themes)\/draft$/, 'ai.create'],
    [/^\/ai\/requests(\/|$)/, 'ai.history'],
    [/^\/ai(\/|$)/, 'ai.use'],
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

/**
 * The audit event catalogue — one place for every action key (used by the mock, the
 * audit trail page, filters and exports). Labels live in i18n under `audit.action.<key>`
 * with dots replaced by underscores (`auth.login.failed` → `audit.action.auth_login_failed`).
 * New features add their actions here as they are built (PROGRESS.md → definition of done).
 */
export const AUDIT_AREAS = [
  'auth',
  'workspace',
  'forms',
  'responses',
  'settings',
  'users',
  'integrations',
  'audit',
] as const

export type AuditArea = (typeof AUDIT_AREAS)[number]

interface AuditEventDefinition {
  area: AuditArea
  icon: string
}

export const AUDIT_EVENTS = {
  // Sign-in & security
  'auth.login.succeeded': { area: 'auth', icon: 'i-lucide-log-in' },
  'auth.login.failed': { area: 'auth', icon: 'i-lucide-shield-x' },
  'auth.login.blocked': { area: 'auth', icon: 'i-lucide-shield-ban' },
  'auth.otp.sent': { area: 'auth', icon: 'i-lucide-send' },
  'auth.otp.failed': { area: 'auth', icon: 'i-lucide-shield-alert' },
  'auth.otp.locked': { area: 'auth', icon: 'i-lucide-lock' },
  'auth.logout': { area: 'auth', icon: 'i-lucide-log-out' },
  'auth.session.revoked': { area: 'auth', icon: 'i-lucide-octagon-x' },
  'auth.password.reset_requested': { area: 'auth', icon: 'i-lucide-key-round' },
  'auth.password.reset': { area: 'auth', icon: 'i-lucide-rotate-ccw-key' },
  // Workspace
  'workspace.created': { area: 'workspace', icon: 'i-lucide-building-2' },
  'workspace.updated': { area: 'workspace', icon: 'i-lucide-building' },
  'workspace.setup_completed': { area: 'workspace', icon: 'i-lucide-party-popper' },
  // Forms
  'forms.created': { area: 'forms', icon: 'i-lucide-file-plus' },
  'forms.updated': { area: 'forms', icon: 'i-lucide-file-pen' },
  'forms.published': { area: 'forms', icon: 'i-lucide-globe' },
  'forms.closed': { area: 'forms', icon: 'i-lucide-circle-stop' },
  'forms.shared': { area: 'forms', icon: 'i-lucide-share-2' },
  'forms.archived': { area: 'forms', icon: 'i-lucide-archive' },
  'forms.deleted': { area: 'forms', icon: 'i-lucide-trash-2' },
  'forms.restored': { area: 'forms', icon: 'i-lucide-archive-restore' },
  // Responses
  'responses.updated': { area: 'responses', icon: 'i-lucide-square-pen' },
  'responses.exported': { area: 'responses', icon: 'i-lucide-file-down' },
  'responses.deleted': { area: 'responses', icon: 'i-lucide-trash' },
  // Settings
  'settings.updated': { area: 'settings', icon: 'i-lucide-settings-2' },
  // Users
  'users.invited': { area: 'users', icon: 'i-lucide-user-plus' },
  'users.role_changed': { area: 'users', icon: 'i-lucide-user-cog' },
  'users.disabled': { area: 'users', icon: 'i-lucide-user-x' },
  'users.enabled': { area: 'users', icon: 'i-lucide-user-check' },
  // Integrations
  'integrations.destination_connected': { area: 'integrations', icon: 'i-lucide-database' },
  'integrations.webhook_created': { area: 'integrations', icon: 'i-lucide-webhook' },
  'integrations.api_key_created': { area: 'integrations', icon: 'i-lucide-key' },
  'integrations.api_key_revoked': { area: 'integrations', icon: 'i-lucide-key-square' },
  // The audit trail itself
  'audit.exported': { area: 'audit', icon: 'i-lucide-file-spreadsheet' },
} as const satisfies Record<string, AuditEventDefinition>

export type AuditAction = keyof typeof AUDIT_EVENTS

export const AUDIT_ACTIONS = Object.keys(AUDIT_EVENTS) as AuditAction[]

/** i18n key suffix for an action (`auth.login.failed` → `auth_login_failed`). */
export const auditActionKey = (action: string) => action.replace(/\./g, '_')

/** Field keys the mock (and later the backend) uses in `changes`; labels under `audit.field.<key>`. */
export const AUDIT_FIELDS = [
  'name',
  'status',
  'folder',
  'role',
  'brand_colour',
  'session_timeout_minutes',
  'sign_in_methods',
  'response_status',
  'industry',
  'size',
  'country',
  'website',
  'logo',
  'language',
  'timezone',
  'currency',
  'date_format',
  'number_format',
  'week_start',
] as const

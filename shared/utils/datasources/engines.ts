/**
 * Connection settings per database engine (F12 M1, owner 2026-10-05: "their connection properties
 * differ"). One catalogue drives the Add connection steps, validation on both sides and the
 * summary on a connection's panel:
 *
 *   MySQL / MariaDB  host · port · database · charset · time zone · TLS mode (disabled → verify identity)
 *   PostgreSQL       host · port · database · sslmode (disable → verify-full) · target session
 *   SQL Server       host · instance · port · database · SQL / Microsoft Entra sign-in ·
 *                    encrypt (mandatory / strict / optional) · trust certificate · application intent
 *   Oracle           host · port · service name / SID / full descriptor · TCPS or
 *                    native network encryption · certificate DN match
 *   every engine     optional SSH tunnel (host, port, user, private key, passphrase) · connect timeout
 *
 * Schemas are chosen in the Access step only (where the response tables go, which other schemas
 * Formalie may use); the server step only says how to reach the database.
 *
 * Labels live in i18n (`dataSources.field.<key>`, hints `dataSources.hint.<key>`, choices
 * `dataSources.option.<key>.<value>`). Secret fields never come back from the API.
 */
import type { DataSourceSecrets, DataSourceSettings } from '#shared/types/datasources'
import type { DbEngine } from '#shared/utils/integrations/databases'

export type FieldStep = 'server' | 'signin' | 'security'
export type FieldType = 'text' | 'number' | 'select' | 'switch' | 'secret' | 'certificate'

export interface EngineField {
  key: string
  step: FieldStep
  type: FieldType
  default?: string | number | boolean
  options?: string[]
  required?: boolean
  /** Shown (and checked) only when this is true for the current settings. */
  when?: (settings: DataSourceSettings) => boolean
  /** Technical example, not translated (hosts, names). */
  placeholder?: string
  /** Under "More options" on its step. */
  advanced?: boolean
  /** Half width beside its neighbour on larger screens. */
  half?: boolean
  /** Checked as a host name / port / PEM block / identifier. */
  format?: 'host' | 'port' | 'pem' | 'identifier' | 'uuid' | 'seconds'
}

export const isSecretField = (field: EngineField) => field.type === 'secret' || field.type === 'certificate'

const is = (key: string, ...values: (string | boolean)[]) => (settings: DataSourceSettings) => values.includes(settings[key] as string | boolean)
const not = (key: string, ...values: string[]) => (settings: DataSourceSettings) => !values.includes(settings[key] as string)

const host = (when?: EngineField['when']): EngineField => ({ key: 'host', step: 'server', type: 'text', required: true, format: 'host', placeholder: 'db.example.net', when })
const port = (value: number, when?: EngineField['when']): EngineField => ({ key: 'port', step: 'server', type: 'number', default: value, required: true, format: 'port', half: true, when })
const timeout = (value: number): EngineField => ({ key: 'connect_timeout', step: 'server', type: 'number', default: value, format: 'seconds', advanced: true, half: true })
const username = (when?: EngineField['when']): EngineField => ({ key: 'username', step: 'signin', type: 'text', required: true, placeholder: 'formalie_app', when })
const password = (when?: EngineField['when']): EngineField => ({ key: 'password', step: 'signin', type: 'secret', required: true, when })

/** Mutual TLS, optional, under More options. */
const clientCertificate = (when: EngineField['when']): EngineField[] => [
  { key: 'client_certificate', step: 'security', type: 'certificate', format: 'pem', advanced: true, when },
  { key: 'client_key', step: 'security', type: 'certificate', format: 'pem', advanced: true, when },
]

/** The SSH tunnel, the same for every engine (the way to reach a database on a private network). */
const SSH: EngineField[] = [
  { key: 'ssh', step: 'security', type: 'switch', default: false },
  { key: 'ssh_host', step: 'security', type: 'text', required: true, format: 'host', placeholder: 'bastion.example.net', when: is('ssh', true) },
  { key: 'ssh_port', step: 'security', type: 'number', default: 22, required: true, format: 'port', half: true, when: is('ssh', true) },
  { key: 'ssh_username', step: 'security', type: 'text', required: true, half: true, placeholder: 'tunnel', when: is('ssh', true) },
  { key: 'ssh_private_key', step: 'security', type: 'certificate', required: true, format: 'pem', when: is('ssh', true) },
  { key: 'ssh_passphrase', step: 'security', type: 'secret', when: is('ssh', true) },
]

const MYSQL_TLS = ['disabled', 'preferred', 'required', 'verify_ca', 'verify_identity']
const mysqlLike = (): EngineField[] => [
  host(),
  port(3306),
  { key: 'database', step: 'server', type: 'text', required: true, half: true, placeholder: 'intake' },
  { key: 'charset', step: 'server', type: 'select', options: ['utf8mb4', 'utf8mb3', 'latin1'], default: 'utf8mb4', advanced: true, half: true },
  { key: 'time_zone', step: 'server', type: 'text', default: '+00:00', advanced: true, half: true, placeholder: '+00:00' },
  timeout(10),
  username(),
  password(),
  { key: 'ssl_mode', step: 'security', type: 'select', options: MYSQL_TLS, default: 'required' },
  { key: 'ca_certificate', step: 'security', type: 'certificate', required: true, format: 'pem', when: is('ssl_mode', 'verify_ca', 'verify_identity') },
  ...clientCertificate(not('ssl_mode', 'disabled')),
  ...SSH,
]

export const ENGINE_FIELDS: Record<DbEngine, EngineField[]> = {
  mysql: mysqlLike(),
  mariadb: mysqlLike(),
  postgresql: [
    host(),
    port(5432),
    { key: 'database', step: 'server', type: 'text', required: true, half: true, placeholder: 'cases' },
    { key: 'target_session_attrs', step: 'server', type: 'select', options: ['any', 'read-write', 'read-only', 'primary', 'standby', 'prefer-standby'], default: 'any', advanced: true, half: true },
    timeout(10),
    username(),
    password(),
    { key: 'ssl_mode', step: 'security', type: 'select', options: ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'], default: 'require' },
    { key: 'ca_certificate', step: 'security', type: 'certificate', required: true, format: 'pem', when: is('ssl_mode', 'verify-ca', 'verify-full') },
    ...clientCertificate(not('ssl_mode', 'disable')),
    ...SSH,
  ],
  sqlserver: [
    host(),
    { key: 'instance', step: 'server', type: 'text', half: true, placeholder: 'SQLEXPRESS', format: 'identifier' },
    port(1433),
    { key: 'database', step: 'server', type: 'text', required: true, half: true, placeholder: 'People' },
    { key: 'application_intent', step: 'server', type: 'select', options: ['read_write', 'read_only'], default: 'read_write', advanced: true, half: true },
    { key: 'multi_subnet_failover', step: 'server', type: 'switch', default: false, advanced: true },
    timeout(15),
    { key: 'auth', step: 'signin', type: 'select', options: ['sql', 'entra_password', 'entra_service_principal'], default: 'sql' },
    username(not('auth', 'entra_service_principal')),
    password(not('auth', 'entra_service_principal')),
    { key: 'tenant_id', step: 'signin', type: 'text', required: true, format: 'uuid', when: is('auth', 'entra_service_principal') },
    { key: 'client_id', step: 'signin', type: 'text', required: true, format: 'uuid', when: is('auth', 'entra_service_principal') },
    { key: 'client_secret', step: 'signin', type: 'secret', required: true, when: is('auth', 'entra_service_principal') },
    { key: 'encrypt', step: 'security', type: 'select', options: ['mandatory', 'strict', 'optional'], default: 'mandatory' },
    { key: 'trust_server_certificate', step: 'security', type: 'switch', default: false, when: is('encrypt', 'mandatory') },
    { key: 'host_name_in_certificate', step: 'security', type: 'text', format: 'host', advanced: true, when: not('encrypt', 'optional') },
    { key: 'ca_certificate', step: 'security', type: 'certificate', format: 'pem', advanced: true, when: not('encrypt', 'optional') },
    ...SSH,
  ],
  oracle: [
    { key: 'connect_by', step: 'server', type: 'select', options: ['service_name', 'sid', 'descriptor'], default: 'service_name' },
    host(not('connect_by', 'descriptor')),
    port(1521, not('connect_by', 'descriptor')),
    { key: 'service_name', step: 'server', type: 'text', required: true, half: true, placeholder: 'FINPDB1', when: is('connect_by', 'service_name') },
    { key: 'sid', step: 'server', type: 'text', required: true, half: true, placeholder: 'ORCL', format: 'identifier', when: is('connect_by', 'sid') },
    { key: 'descriptor', step: 'server', type: 'text', required: true, placeholder: '(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=db.example.net)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=FINPDB1)))', when: is('connect_by', 'descriptor') },
    timeout(10),
    username(),
    password(),
    { key: 'protocol', step: 'security', type: 'select', options: ['tcps', 'tcp'], default: 'tcps', when: not('connect_by', 'descriptor') },
    { key: 'network_encryption', step: 'security', type: 'select', options: ['required', 'requested', 'accepted'], default: 'required', when: settings => settings.protocol === 'tcp' && settings.connect_by !== 'descriptor' },
    { key: 'ca_certificate', step: 'security', type: 'certificate', format: 'pem', when: settings => settings.protocol !== 'tcp' || settings.connect_by === 'descriptor' },
    { key: 'ssl_server_dn_match', step: 'security', type: 'switch', default: true, when: settings => settings.protocol !== 'tcp' || settings.connect_by === 'descriptor' },
    ...SSH,
  ],
}

/** The fields to show for these settings (a step, or all of them). */
export function fieldsFor(engine: DbEngine, settings: DataSourceSettings, step?: FieldStep): EngineField[] {
  return ENGINE_FIELDS[engine].filter(field => (!step || field.step === step) && (!field.when || field.when(settings)))
}

/** Defaults for a new connection (secrets excluded). */
export function defaultSettings(engine: DbEngine): DataSourceSettings {
  const settings: DataSourceSettings = {}
  for (const field of ENGINE_FIELDS[engine]) {
    if (isSecretField(field)) continue
    settings[field.key] = field.default ?? (field.type === 'switch' ? false : field.type === 'number' ? 0 : '')
  }
  return settings
}

/** Keep only this engine's non-secret keys (anything else in a request is dropped). */
export function cleanSettings(engine: DbEngine, input: DataSourceSettings): DataSourceSettings {
  const base = defaultSettings(engine)
  for (const key of Object.keys(base)) {
    const value = input[key]
    if (value === undefined || value === null) continue
    const kind = typeof base[key]
    base[key] = kind === 'number' ? Number(value) : kind === 'boolean' ? value === true || value === 'true' : String(value).trim()
  }
  return base
}

// ── Checks (the same on both sides; the UI turns codes into translated messages) ─────────

export type FieldProblem = 'required' | 'host' | 'host_blocked' | 'port' | 'pem' | 'identifier' | 'uuid' | 'seconds'

const HOST = /^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$/
const IPV4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/
const IPV6 = /^\[?[0-9A-Fa-f:.]+\]?$/
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const IDENTIFIER = /^[\p{L}_][\p{L}\p{N}_$#@ .-]{0,127}$/u

/**
 * Formalie's servers never connect to themselves or to cloud metadata addresses (protection
 * against server-side request forgery). A database on a private network is reached through an
 * SSH tunnel or a private link. The backend repeats this check on the resolved address.
 */
export function isBlockedHost(value: string): boolean {
  const host = value.trim().toLowerCase().replace(/^\[|\]$/g, '').replace(/\.$/, '')
  if (host === 'localhost' || host.endsWith('.localhost') || host === 'metadata.google.internal') return true
  if (host === '::1' || host === '::' || host.startsWith('fe80:') || host.startsWith('::ffff:127.')) return true
  const ip = IPV4.exec(host)
  if (!ip) return false
  const [a, b] = [Number(ip[1]), Number(ip[2])]
  return a === 0 || a === 127 || (a === 169 && b === 254) || (a === 100 && b >= 64 && b <= 127) || a >= 224
}

function checkValue(field: EngineField, value: unknown): FieldProblem | null {
  const text = typeof value === 'string' ? value.trim() : value
  const empty = text === '' || text === undefined || text === null
  if (empty) return field.required ? 'required' : null
  switch (field.format) {
    case 'host': {
      const name = String(text)
      if (!HOST.test(name) && !IPV4.test(name) && !IPV6.test(name)) return 'host'
      if (IPV4.test(name) && name.split('.').some(part => Number(part) > 255)) return 'host'
      return isBlockedHost(name) ? 'host_blocked' : null
    }
    case 'port':
      return Number.isInteger(Number(text)) && Number(text) >= 1 && Number(text) <= 65535 ? null : 'port'
    case 'seconds':
      return Number.isInteger(Number(text)) && Number(text) >= 1 && Number(text) <= 120 ? null : 'seconds'
    case 'pem':
      return /-----BEGIN [A-Z0-9 ]+-----[\s\S]+-----END [A-Z0-9 ]+-----/.test(String(text)) ? null : 'pem'
    case 'uuid':
      return UUID.test(String(text)) ? null : 'uuid'
    case 'identifier':
      return IDENTIFIER.test(String(text)) ? null : 'identifier'
    default:
      return null
  }
}

/**
 * Problems per field for a configuration. `secretsSet`: secrets already stored for a saved
 * connection, so leaving them empty keeps them.
 */
export function checkConfig(engine: DbEngine, settings: DataSourceSettings, secrets: DataSourceSecrets = {}, secretsSet: string[] = [], step?: FieldStep): Record<string, FieldProblem> {
  const problems: Record<string, FieldProblem> = {}
  for (const field of fieldsFor(engine, settings, step)) {
    if (field.type === 'switch' || field.type === 'select') continue
    const kept = isSecretField(field) && !secrets[field.key] && secretsSet.includes(field.key)
    if (kept) continue
    const problem = checkValue(field, isSecretField(field) ? secrets[field.key] : settings[field.key])
    if (problem) problems[field.key] = problem
  }
  return problems
}

/** Only the secrets this engine and these settings use (stale ones are dropped). */
export function cleanSecrets(engine: DbEngine, settings: DataSourceSettings, secrets: DataSourceSecrets = {}): DataSourceSecrets {
  const keys = new Set(fieldsFor(engine, settings).filter(isSecretField).map(field => field.key))
  return Object.fromEntries(Object.entries(secrets).filter(([key, value]) => keys.has(key) && typeof value === 'string' && value.trim() !== ''))
}

/** "db.example.net:5432", or the host inside an Oracle descriptor. */
export function addressOf(engine: DbEngine, settings: DataSourceSettings): string {
  if (engine === 'oracle' && settings.connect_by === 'descriptor') {
    const descriptor = String(settings.descriptor ?? '')
    const found = /HOST\s*=\s*([^)\s]+)/i.exec(descriptor)
    const port = /PORT\s*=\s*(\d+)/i.exec(descriptor)
    return found ? `${found[1]}${port ? `:${port[1]}` : ''}` : ''
  }
  const instance = engine === 'sqlserver' && settings.instance ? `\\${settings.instance}` : ''
  return settings.host ? `${settings.host}${instance}:${settings.port}` : ''
}

/** The database (Oracle: service name, SID or the descriptor's service). */
export function databaseNameOf(engine: DbEngine, settings: DataSourceSettings): string {
  if (engine !== 'oracle') return String(settings.database ?? '')
  if (settings.connect_by === 'sid') return String(settings.sid ?? '')
  if (settings.connect_by === 'descriptor') return /SERVICE_NAME\s*=\s*([^)\s]+)/i.exec(String(settings.descriptor ?? ''))?.[1] ?? ''
  return String(settings.service_name ?? '')
}

/** The engine's usual schema for existing tables (MySQL / MariaDB: the database; Oracle: the account's own). */
export function defaultSchemaOf(engine: DbEngine, settings: DataSourceSettings): string {
  if (engine === 'mysql' || engine === 'mariadb') return String(settings.database ?? '')
  if (engine === 'oracle') return String(settings.username || '').toUpperCase()
  return engine === 'postgresql' ? 'public' : 'dbo'
}

/** Is traffic to the database encrypted with these settings? */
export function isEncrypted(engine: DbEngine, settings: DataSourceSettings): boolean {
  switch (engine) {
    case 'mysql':
    case 'mariadb':
      return !['disabled', 'preferred'].includes(String(settings.ssl_mode))
    case 'postgresql':
      return ['require', 'verify-ca', 'verify-full'].includes(String(settings.ssl_mode))
    case 'sqlserver':
      return settings.encrypt !== 'optional'
    case 'oracle':
      return settings.connect_by === 'descriptor' || settings.protocol !== 'tcp' || settings.network_encryption === 'required'
  }
}

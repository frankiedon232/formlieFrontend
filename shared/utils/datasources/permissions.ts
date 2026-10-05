/**
 * What Formalie does on a connected database and the permissions each engine needs for it (F12,
 * owner 2026-10-05: "always tell the user which permissions to grant, so that nothing breaks").
 *
 * Least privilege: a dedicated account, only the levels the connection uses.
 *   read       connect, read the structure, row counts, read rows (explorer, exports, read
 *              queries, option lists), cancel its own running query
 *   write      add, change and delete rows (form deliveries, update-or-insert, row edits,
 *              imports), use sequences for generated ids
 *   structure  create tables from a form, add columns for new fields, add the unique index an
 *              update-or-insert needs
 *
 * `grantScript()` writes the statements for the connection's own database, schemas and account
 * name; the guide shows them with a Copy button. The connection test checks every operation.
 * Operation labels: `dataSources.op.<key>`; block notes: `dataSources.grant.note.<key>`.
 */
import type { DataSourceAccessSettings, DataSourceSettings } from '#shared/types/datasources'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { databaseNameOf, defaultSchemaOf, isEncrypted } from './engines'

export type PermissionLevel = 'read' | 'write' | 'structure'

export interface DbOperation {
  key: string
  level: PermissionLevel
  icon: string
  /** Only these engines need it (e.g. sequences). */
  engines?: DbEngine[]
}

export const DB_OPERATIONS: DbOperation[] = [
  { key: 'connect', level: 'read', icon: 'i-lucide-plug' },
  { key: 'read_schema', level: 'read', icon: 'i-lucide-network' },
  { key: 'row_counts', level: 'read', icon: 'i-lucide-hash' },
  { key: 'read_rows', level: 'read', icon: 'i-lucide-table-2' },
  { key: 'cancel', level: 'read', icon: 'i-lucide-circle-stop' },
  { key: 'insert', level: 'write', icon: 'i-lucide-list-plus' },
  { key: 'update', level: 'write', icon: 'i-lucide-pencil-line' },
  { key: 'delete', level: 'write', icon: 'i-lucide-list-x' },
  { key: 'sequences', level: 'write', icon: 'i-lucide-list-ordered', engines: ['postgresql', 'oracle'] },
  { key: 'create_table', level: 'structure', icon: 'i-lucide-table-properties' },
  { key: 'alter_table', level: 'structure', icon: 'i-lucide-columns-3' },
  { key: 'create_index', level: 'structure', icon: 'i-lucide-key-round' },
]

/** The privilege behind each operation, per engine (technical names, shown as they are). */
export const PRIVILEGES: Record<DbEngine, Record<string, string>> = {
  mysql: {
    connect: 'USAGE (login)',
    read_schema: 'SELECT, SHOW VIEW',
    row_counts: 'SELECT (information_schema.TABLES)',
    read_rows: 'SELECT',
    cancel: 'KILL QUERY on its own session',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    create_table: 'CREATE',
    alter_table: 'ALTER',
    create_index: 'INDEX',
  },
  mariadb: {
    connect: 'USAGE (login)',
    read_schema: 'SELECT, SHOW VIEW',
    row_counts: 'SELECT (information_schema.TABLES)',
    read_rows: 'SELECT',
    cancel: 'KILL QUERY on its own session',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    create_table: 'CREATE',
    alter_table: 'ALTER',
    create_index: 'INDEX',
  },
  postgresql: {
    connect: 'LOGIN, CONNECT on the database',
    read_schema: 'USAGE on the schema',
    row_counts: 'pg_class statistics (no grant needed)',
    read_rows: 'SELECT',
    cancel: 'pg_cancel_backend on its own session',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    sequences: 'USAGE, SELECT on sequences',
    create_table: 'CREATE on the schema',
    alter_table: 'table owner (tables it created)',
    create_index: 'table owner (tables it created)',
  },
  sqlserver: {
    connect: 'login + database user',
    read_schema: 'VIEW DEFINITION',
    row_counts: 'VIEW DATABASE STATE',
    read_rows: 'SELECT',
    cancel: 'attention signal (no grant needed)',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    create_table: 'CREATE TABLE + ALTER on the schema',
    alter_table: 'ALTER on the schema',
    create_index: 'ALTER on the schema',
  },
  oracle: {
    connect: 'CREATE SESSION',
    read_schema: 'object grants (ALL_* views)',
    row_counts: 'ALL_TABLES statistics',
    read_rows: 'SELECT',
    cancel: 'break on its own session (no grant needed)',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    sequences: 'SELECT on sequences',
    create_table: 'CREATE TABLE (+ tablespace quota)',
    alter_table: 'ALTER (tables it created)',
    create_index: 'CREATE INDEX (tables it created)',
  },
}

/** The levels a connection uses. */
export function levelsFor(access: DataSourceAccessSettings): PermissionLevel[] {
  if (access.mode === 'read_only') return ['read']
  return access.structure ? ['read', 'write', 'structure'] : ['read', 'write']
}

/** The operations that apply to this engine, and whether this connection needs each. */
export function operationsFor(engine: DbEngine, access: DataSourceAccessSettings) {
  const levels = levelsFor(access)
  return DB_OPERATIONS.filter(operation => !operation.engines || operation.engines.includes(engine)).map(operation => ({
    ...operation,
    privilege: PRIVILEGES[engine][operation.key] ?? '',
    needed: levels.includes(operation.level),
  }))
}

// ── Grant script ─────────────────────────────────────────────────────────────────────────

export interface GrantBlock {
  /** account · read · write · structure */
  key: 'account' | PermissionLevel
  sql: string
  /** i18n keys under dataSources.grant.note */
  notes: string[]
}

export interface GrantOptions {
  /** Oracle 23ai and later grant per schema; earlier versions per table. */
  oracle23?: boolean
}

const ACCOUNT = 'formalie_app'

const quote = {
  mysql: (name: string) => `\`${name.replace(/`/g, '``')}\``,
  postgresql: (name: string) => `"${name.replace(/"/g, '""')}"`,
  sqlserver: (name: string) => `[${name.replace(/]/g, ']]')}]`,
  oracle: (name: string) => `"${name.toUpperCase().replace(/"/g, '""')}"`,
}
const literal = (value: string) => `'${value.replace(/'/g, "''")}'`

function schemasOf(engine: DbEngine, settings: DataSourceSettings, access: DataSourceAccessSettings): string[] {
  const list = access.schemas.filter(Boolean)
  return list.length ? list : [defaultSchemaOf(engine, settings) || (engine === 'oracle' ? 'APP' : engine === 'sqlserver' ? 'dbo' : 'public')]
}

/** The statements to run (as an administrator) for this connection. */
export function grantScript(engine: DbEngine, settings: DataSourceSettings, access: DataSourceAccessSettings, options: GrantOptions = {}): GrantBlock[] {
  const levels = levelsFor(access)
  const user = String(settings.username || '').trim() || ACCOUNT
  const blocks: GrantBlock[] = []
  const add = (key: GrantBlock['key'], lines: string[], notes: string[] = []) => {
    if (key === 'account' || levels.includes(key)) blocks.push({ key, sql: lines.join('\n'), notes })
  }

  switch (engine) {
    case 'mysql':
    case 'mariadb': {
      const who = `${literal(user)}@'%'`
      const databases = access.schemas.length ? access.schemas : [String(settings.database || 'your_database')]
      const on = (privileges: string) => databases.map(db => `GRANT ${privileges} ON ${quote.mysql(db)}.* TO ${who};`)
      add('account', [`CREATE USER ${who} IDENTIFIED BY '<password>'${isEncrypted(engine, settings) ? ' REQUIRE SSL' : ''} WITH MAX_USER_CONNECTIONS 10;`], ['host_limit', 'pool'])
      add('read', on('SELECT, SHOW VIEW'))
      add('write', on('INSERT, UPDATE, DELETE'))
      add('structure', on('CREATE, ALTER, INDEX, REFERENCES'))
      break
    }
    case 'postgresql': {
      const role = quote.postgresql(user)
      const schemas = schemasOf(engine, settings, access).map(quote.postgresql)
      const each = (fn: (schema: string) => string[]) => schemas.flatMap(fn)
      add('account', [`CREATE ROLE ${role} LOGIN PASSWORD '<password>' CONNECTION LIMIT 10;`, `GRANT CONNECT ON DATABASE ${quote.postgresql(String(settings.database || 'your_database'))} TO ${role};`], ['pool'])
      add(
        'read',
        each(schema => [`GRANT USAGE ON SCHEMA ${schema} TO ${role};`, `GRANT SELECT ON ALL TABLES IN SCHEMA ${schema} TO ${role};`, `ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT SELECT ON TABLES TO ${role};`]),
        ['default_privileges'],
      )
      add(
        'write',
        each(schema => [
          `GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ${schema} TO ${role};`,
          `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ${schema} TO ${role};`,
          `ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT INSERT, UPDATE, DELETE ON TABLES TO ${role};`,
          `ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT USAGE, SELECT ON SEQUENCES TO ${role};`,
        ]),
      )
      add('structure', each(schema => [`GRANT CREATE ON SCHEMA ${schema} TO ${role};`]), ['owner_alter'])
      break
    }
    case 'sqlserver': {
      const principal = quote.sqlserver(settings.auth === 'entra_service_principal' ? String(settings.client_id || 'formalie-app') : user)
      const database = quote.sqlserver(String(settings.database || 'your_database'))
      const schemas = schemasOf(engine, settings, access).map(quote.sqlserver)
      const each = (fn: (schema: string) => string) => schemas.map(fn)
      const entra = settings.auth === 'entra_password' || settings.auth === 'entra_service_principal'
      add(
        'account',
        entra
          ? [`USE ${database};`, `CREATE USER ${principal} FROM EXTERNAL PROVIDER WITH DEFAULT_SCHEMA = ${schemas[0]};`]
          : [`USE [master];`, `CREATE LOGIN ${principal} WITH PASSWORD = '<password>', CHECK_POLICY = ON;`, `USE ${database};`, `CREATE USER ${principal} FOR LOGIN ${principal} WITH DEFAULT_SCHEMA = ${schemas[0]};`],
        entra ? ['entra'] : ['contained'],
      )
      add('read', [...each(schema => `GRANT SELECT, VIEW DEFINITION ON SCHEMA::${schema} TO ${principal};`), `GRANT VIEW DATABASE STATE TO ${principal};`])
      add('write', each(schema => `GRANT INSERT, UPDATE, DELETE ON SCHEMA::${schema} TO ${principal};`))
      add('structure', [`GRANT CREATE TABLE TO ${principal};`, ...each(schema => `GRANT ALTER, REFERENCES ON SCHEMA::${schema} TO ${principal};`)])
      break
    }
    case 'oracle': {
      const account = quote.oracle(user)
      const owners = schemasOf(engine, settings, access).map(schema => schema.toUpperCase())
      const loop = (privileges: string, view = 'all_tables', column = 'table_name', ownerColumn = 'owner') =>
        owners.flatMap(owner => [
          'BEGIN',
          `  FOR t IN (SELECT ${column} AS name FROM ${view} WHERE ${ownerColumn} = ${literal(owner)}) LOOP`,
          `    EXECUTE IMMEDIATE 'GRANT ${privileges} ON ${quote.oracle(owner).replace(/'/g, "''")}."' || t.name || '" TO ${account.replace(/'/g, "''")}';`,
          '  END LOOP;',
          'END;',
          '/',
        ])
      add('account', [`CREATE USER ${account} IDENTIFIED BY "<password>";`, `GRANT CREATE SESSION TO ${account};`], ['no_sysdba'])
      if (options.oracle23) {
        add('read', owners.map(owner => `GRANT SELECT ANY TABLE ON SCHEMA ${quote.oracle(owner)} TO ${account};`))
        add('write', owners.flatMap(owner => [`GRANT INSERT ANY TABLE, UPDATE ANY TABLE, DELETE ANY TABLE ON SCHEMA ${quote.oracle(owner)} TO ${account};`, `GRANT SELECT ANY SEQUENCE ON SCHEMA ${quote.oracle(owner)} TO ${account};`]))
        add('structure', owners.map(owner => `GRANT CREATE ANY TABLE, ALTER ANY TABLE, CREATE ANY INDEX ON SCHEMA ${quote.oracle(owner)} TO ${account};`))
      } else {
        add('read', [...loop('SELECT'), ...loop('SELECT', 'all_views', 'view_name')], ['oracle_new_tables'])
        add('write', [...loop('INSERT, UPDATE, DELETE'), ...loop('SELECT', 'all_sequences', 'sequence_name', 'sequence_owner')], ['oracle_new_tables'])
        add('structure', [`GRANT CREATE TABLE TO ${account};`, `ALTER USER ${account} QUOTA 1G ON USERS;`], ['oracle_own_schema'])
      }
      break
    }
  }
  return blocks
}

/** The whole script as one text (Copy all). */
export const grantScriptText = (blocks: GrantBlock[]) => blocks.map(block => block.sql).join('\n\n')

/** The database the script runs against, for the guide's heading. */
export const grantTarget = (engine: DbEngine, settings: DataSourceSettings) => databaseNameOf(engine, settings)

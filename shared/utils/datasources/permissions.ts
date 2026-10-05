/**
 * What Formalie does on a connected database and the permissions each engine needs for it (F12,
 * owner 2026-10-05: always tell people which permissions to grant, so that nothing breaks).
 *
 * A connection exists to store responses (owner 2026-10-05, not negotiable), so one level is
 * always required and two are optional:
 *   own    (required)  sign in, create Formalie's tables (one per form, named with the prefix),
 *                      read and write their rows, add columns, add the unique key each response
 *                      row is found by, cancel its own query: everything, in its own tables only
 *   read   (optional)  the organisation's other tables: structure, row counts, rows (explorer,
 *                      queries, option lists from their data)
 *   write  (optional)  full access: add, change and delete rows in those tables (row edits,
 *                      imports, responses stored in a table of theirs), their sequences, and
 *                      create and change tables in their schemas
 *
 * Where Formalie's tables live keeps them apart from the rest: PostgreSQL, tables it owns in the
 * chosen schema; SQL Server, a schema of its own that the account owns; Oracle, the account's own
 * schema; MySQL / MariaDB grant per database, so its rights there cover the whole database (a note
 * says so). `grantScript()` writes the statements for the connection's own names; the test checks
 * every operation. Labels: `dataSources.op.<key>`, notes `dataSources.grant.note.<key>`.
 */
import type { DataSourceAccessSettings, DataSourceSettings } from '#shared/types/datasources'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { databaseNameOf, defaultSchemaOf, isEncrypted } from './engines'

export type PermissionLevel = 'own' | 'read' | 'write'

export interface DbOperation {
  key: string
  level: PermissionLevel
  icon: string
  /** Only these engines need it. */
  engines?: DbEngine[]
}

export const DB_OPERATIONS: DbOperation[] = [
  { key: 'connect', level: 'own', icon: 'i-lucide-plug' },
  { key: 'create_table', level: 'own', icon: 'i-lucide-table-properties' },
  { key: 'own_rows', level: 'own', icon: 'i-lucide-inbox' },
  { key: 'alter_table', level: 'own', icon: 'i-lucide-columns-3' },
  { key: 'create_index', level: 'own', icon: 'i-lucide-key-round' },
  { key: 'cancel', level: 'own', icon: 'i-lucide-circle-stop' },
  { key: 'read_schema', level: 'read', icon: 'i-lucide-network' },
  { key: 'row_counts', level: 'read', icon: 'i-lucide-hash' },
  { key: 'read_rows', level: 'read', icon: 'i-lucide-table-2' },
  { key: 'insert', level: 'write', icon: 'i-lucide-list-plus' },
  { key: 'update', level: 'write', icon: 'i-lucide-pencil-line' },
  { key: 'delete', level: 'write', icon: 'i-lucide-list-x' },
  { key: 'sequences', level: 'write', icon: 'i-lucide-list-ordered', engines: ['postgresql', 'oracle'] },
  { key: 'other_structure', level: 'write', icon: 'i-lucide-table-properties' },
]

const MYSQL: Record<string, string> = {
  connect: 'USAGE (login)',
  create_table: 'CREATE',
  own_rows: 'SELECT, INSERT, UPDATE, DELETE',
  alter_table: 'ALTER',
  create_index: 'INDEX',
  cancel: 'KILL QUERY on its own session',
  read_schema: 'SELECT, SHOW VIEW',
  row_counts: 'SELECT (information_schema.TABLES)',
  read_rows: 'SELECT',
  insert: 'INSERT',
  update: 'UPDATE',
  delete: 'DELETE',
  other_structure: 'CREATE, ALTER, INDEX',
}

/** The privilege behind each operation, per engine (technical names, shown as they are). */
export const PRIVILEGES: Record<DbEngine, Record<string, string>> = {
  mysql: MYSQL,
  mariadb: MYSQL,
  postgresql: {
    connect: 'LOGIN, CONNECT on the database',
    create_table: 'USAGE, CREATE on its schema',
    own_rows: 'table owner (tables it created)',
    alter_table: 'table owner (tables it created)',
    create_index: 'table owner (tables it created)',
    cancel: 'pg_cancel_backend on its own session',
    read_schema: 'USAGE on the schema',
    row_counts: 'pg_class statistics (no grant needed)',
    read_rows: 'SELECT',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    sequences: 'USAGE, SELECT on sequences',
    other_structure: 'CREATE on the schema (new tables); owner to change existing ones',
  },
  sqlserver: {
    connect: 'login + database user',
    create_table: 'CREATE TABLE + owner of its schema',
    own_rows: 'owner of its schema',
    alter_table: 'owner of its schema',
    create_index: 'owner of its schema',
    cancel: 'attention signal (no grant needed)',
    read_schema: 'VIEW DEFINITION',
    row_counts: 'VIEW DATABASE STATE',
    read_rows: 'SELECT',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    other_structure: 'CREATE TABLE + ALTER on the schema',
  },
  oracle: {
    connect: 'CREATE SESSION',
    create_table: 'CREATE TABLE + quota (its own schema)',
    own_rows: 'table owner (its own schema)',
    alter_table: 'table owner (its own schema)',
    create_index: 'table owner (its own schema)',
    cancel: 'break on its own session (no grant needed)',
    read_schema: 'object grants (ALL_* views)',
    row_counts: 'ALL_TABLES statistics',
    read_rows: 'SELECT',
    insert: 'INSERT',
    update: 'UPDATE',
    delete: 'DELETE',
    sequences: 'SELECT on sequences',
    other_structure: 'CREATE / ALTER ANY TABLE on the schema (23ai)',
  },
}

/** A new connection: Formalie's tables with the first prefix, read and write on the rest (owner default). */
export const DEFAULT_ACCESS: DataSourceAccessSettings = { table_prefix: 'formalie_', tables_schema: '', other: 'read_write', schemas: [] }

/** The levels a connection uses: its own tables always. */
export function levelsFor(access: DataSourceAccessSettings): PermissionLevel[] {
  return access.other === 'read_write' ? ['own', 'read', 'write'] : access.other === 'read' ? ['own', 'read'] : ['own']
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

/** Can Formalie's own tables be set to a schema of their own on this engine? */
export const hasTablesSchema = (engine: DbEngine) => engine === 'postgresql' || engine === 'sqlserver'

/** Where Formalie's tables live (a schema; MySQL / MariaDB: the database). */
export function tablesSchemaOf(engine: DbEngine, settings: DataSourceSettings, access: DataSourceAccessSettings): string {
  switch (engine) {
    case 'postgresql':
      return access.tables_schema || 'public'
    case 'sqlserver':
      return access.tables_schema || 'formalie'
    case 'oracle':
      return String(settings.username || ACCOUNT).toUpperCase()
    default:
      return String(settings.database || '')
  }
}

// ── Grant script ─────────────────────────────────────────────────────────────────────────

export interface GrantBlock {
  /** account · own · read · write */
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

/** Schemas with the organisation's other tables (MySQL / MariaDB: databases). */
function otherSchemas(engine: DbEngine, settings: DataSourceSettings, access: DataSourceAccessSettings): string[] {
  const list = access.schemas.filter(Boolean)
  if (list.length) return list
  if (engine === 'mysql' || engine === 'mariadb') return [String(settings.database || 'your_database')]
  if (engine === 'oracle') return ['YOUR_SCHEMA']
  return [defaultSchemaOf(engine, settings) || (engine === 'sqlserver' ? 'dbo' : 'public')]
}

/** The statements to run (as an administrator) for this connection. */
export function grantScript(engine: DbEngine, settings: DataSourceSettings, access: DataSourceAccessSettings, options: GrantOptions = {}): GrantBlock[] {
  const levels = levelsFor(access)
  const user = String(settings.username || '').trim() || ACCOUNT
  const blocks: GrantBlock[] = []
  const add = (key: GrantBlock['key'], lines: string[], notes: string[] = []) => {
    if ((key === 'account' || levels.includes(key)) && lines.length) blocks.push({ key, sql: lines.join('\n'), notes })
  }
  const others = otherSchemas(engine, settings, access)

  switch (engine) {
    case 'mysql':
    case 'mariadb': {
      const who = `${literal(user)}@'%'`
      const own = tablesSchemaOf(engine, settings, access) || 'your_database'
      // Other databases than its own need their own grants; inside its own database the rights already cover everything.
      const extra = others.filter(db => db !== own)
      const on = (privileges: string, list: string[]) => list.map(db => `GRANT ${privileges} ON ${quote.mysql(db)}.* TO ${who};`)
      add('account', [`CREATE USER ${who} IDENTIFIED BY '<password>'${isEncrypted(engine, settings) ? ' REQUIRE SSL' : ''} WITH MAX_USER_CONNECTIONS 10;`], ['host_limit', 'pool'])
      add('own', on('CREATE, ALTER, INDEX, REFERENCES, SELECT, INSERT, UPDATE, DELETE', [own]), ['mysql_database'])
      add('read', on('SELECT, SHOW VIEW', extra))
      add('write', on('INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX', extra))
      // Nothing more to run: the block only explains why (no statements, a note).
      if (levels.includes('read') && !extra.length) blocks.push({ key: levels.includes('write') ? 'write' : 'read', sql: '', notes: ['mysql_covered'] })
      break
    }
    case 'postgresql': {
      const role = quote.postgresql(user)
      const own = quote.postgresql(tablesSchemaOf(engine, settings, access))
      const each = (fn: (schema: string) => string[]) => others.map(quote.postgresql).flatMap(fn)
      add('account', [`CREATE ROLE ${role} LOGIN PASSWORD '<password>' CONNECTION LIMIT 10;`, `GRANT CONNECT ON DATABASE ${quote.postgresql(String(settings.database || 'your_database'))} TO ${role};`], ['pool'])
      add('own', [`GRANT USAGE, CREATE ON SCHEMA ${own} TO ${role};`], ['owner_tables'])
      add('read', each(schema => [`GRANT USAGE ON SCHEMA ${schema} TO ${role};`, `GRANT SELECT ON ALL TABLES IN SCHEMA ${schema} TO ${role};`, `ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT SELECT ON TABLES TO ${role};`]), ['default_privileges'])
      add(
        'write',
        each(schema => [
          `GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ${schema} TO ${role};`,
          `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ${schema} TO ${role};`,
          `ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT INSERT, UPDATE, DELETE ON TABLES TO ${role};`,
          `ALTER DEFAULT PRIVILEGES IN SCHEMA ${schema} GRANT USAGE, SELECT ON SEQUENCES TO ${role};`,
          `GRANT CREATE ON SCHEMA ${schema} TO ${role};`,
        ]),
        ['owner_alter_other'],
      )
      break
    }
    case 'sqlserver': {
      const principal = quote.sqlserver(settings.auth === 'entra_service_principal' ? String(settings.client_id || 'formalie-app') : user)
      const database = quote.sqlserver(String(settings.database || 'your_database'))
      const own = quote.sqlserver(tablesSchemaOf(engine, settings, access))
      const each = (fn: (schema: string) => string) => others.map(quote.sqlserver).map(fn)
      const entra = settings.auth === 'entra_password' || settings.auth === 'entra_service_principal'
      add(
        'account',
        entra
          ? [`USE ${database};`, `CREATE USER ${principal} FROM EXTERNAL PROVIDER WITH DEFAULT_SCHEMA = ${own};`]
          : [`USE [master];`, `CREATE LOGIN ${principal} WITH PASSWORD = '<password>', CHECK_POLICY = ON;`, `USE ${database};`, `CREATE USER ${principal} FOR LOGIN ${principal} WITH DEFAULT_SCHEMA = ${own};`],
        entra ? ['entra'] : ['contained'],
      )
      add('own', [`CREATE SCHEMA ${own} AUTHORIZATION ${principal};`, `GRANT CREATE TABLE TO ${principal};`], ['own_schema'])
      add('read', [...each(schema => `GRANT SELECT, VIEW DEFINITION ON SCHEMA::${schema} TO ${principal};`), `GRANT VIEW DATABASE STATE TO ${principal};`])
      add('write', [...each(schema => `GRANT INSERT, UPDATE, DELETE, ALTER ON SCHEMA::${schema} TO ${principal};`), `GRANT CREATE TABLE TO ${principal};`])
      break
    }
    case 'oracle': {
      const account = quote.oracle(user)
      const owners = others.map(schema => schema.toUpperCase())
      const loop = (privileges: string, view = 'all_tables', column = 'table_name', ownerColumn = 'owner') =>
        owners.flatMap(owner => [
          'BEGIN',
          `  FOR t IN (SELECT ${column} AS name FROM ${view} WHERE ${ownerColumn} = ${literal(owner)}) LOOP`,
          `    EXECUTE IMMEDIATE 'GRANT ${privileges} ON ${quote.oracle(owner).replace(/'/g, "''")}."' || t.name || '" TO ${account.replace(/'/g, "''")}';`,
          '  END LOOP;',
          'END;',
          '/',
        ])
      add('account', [`CREATE USER ${account} IDENTIFIED BY "<password>";`, `GRANT CREATE SESSION TO ${account};`])
      add('own', [`GRANT CREATE TABLE, CREATE SEQUENCE TO ${account};`, `ALTER USER ${account} QUOTA 1G ON USERS;`], ['oracle_own_schema'])
      if (options.oracle23) {
        add('read', owners.map(owner => `GRANT SELECT ANY TABLE ON SCHEMA ${quote.oracle(owner)} TO ${account};`))
        add('write', owners.flatMap(owner => [`GRANT INSERT ANY TABLE, UPDATE ANY TABLE, DELETE ANY TABLE ON SCHEMA ${quote.oracle(owner)} TO ${account};`, `GRANT SELECT ANY SEQUENCE ON SCHEMA ${quote.oracle(owner)} TO ${account};`, `GRANT CREATE ANY TABLE, ALTER ANY TABLE, CREATE ANY INDEX ON SCHEMA ${quote.oracle(owner)} TO ${account};`]))
      } else {
        add('read', [...loop('SELECT'), ...loop('SELECT', 'all_views', 'view_name')], ['oracle_new_tables'])
        add('write', [...loop('INSERT, UPDATE, DELETE, ALTER'), ...loop('SELECT', 'all_sequences', 'sequence_name', 'sequence_owner')], ['oracle_new_tables', 'oracle_create_other'])
      }
      break
    }
  }
  return blocks
}

/** The whole script as one text (Copy all). */
export const grantScriptText = (blocks: GrantBlock[]) => blocks.filter(block => block.sql).map(block => block.sql).join('\n\n')

/** The database the script runs against, for the guide's heading. */
export const grantTarget = (engine: DbEngine, settings: DataSourceSettings) => databaseNameOf(engine, settings)

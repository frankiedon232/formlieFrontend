import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { TEST_STEPS, type DataSourceAccessSettings } from '../../shared/types/datasources'
import { ENGINE_FIELDS, addressOf, checkConfig, cleanSecrets, cleanSettings, databaseNameOf, defaultSettings, fieldsFor, isBlockedHost, isEncrypted } from '../../shared/utils/datasources/engines'
import { DB_OPERATIONS, grantScript, grantScriptText, levelsFor, operationsFor, tablesSchemaOf } from '../../shared/utils/datasources/permissions'
import { DB_ENGINES } from '../../shared/utils/integrations/databases'

const readOnly: DataSourceAccessSettings = { table_prefix: 'formalie_', tables_schema: '', other: 'read', schemas: [] }
const ownOnly: DataSourceAccessSettings = { ...readOnly, other: 'none' }
const full: DataSourceAccessSettings = { ...readOnly, other: 'read_write' }

describe('engine catalogue', () => {
  it('every engine has server, sign-in and security fields and secure defaults', () => {
    for (const engine of DB_ENGINES) {
      const steps = new Set(ENGINE_FIELDS[engine].map(field => field.step))
      expect([...steps].sort(), engine).toEqual(['security', 'server', 'signin'])
      expect(isEncrypted(engine, defaultSettings(engine)), `${engine} encrypts by default`).toBe(true)
      expect(defaultSettings(engine)).not.toHaveProperty('password')
    }
  })

  it('uses each engine’s own properties', () => {
    expect(defaultSettings('postgresql')).toMatchObject({ port: 5432, schema: 'public', ssl_mode: 'require' })
    expect(defaultSettings('mysql')).toMatchObject({ port: 3306, charset: 'utf8mb4', ssl_mode: 'required' })
    expect(defaultSettings('sqlserver')).toMatchObject({ port: 1433, schema: 'dbo', auth: 'sql', encrypt: 'mandatory', trust_server_certificate: false })
    expect(defaultSettings('oracle')).toMatchObject({ port: 1521, connect_by: 'service_name', protocol: 'tcps' })
  })

  it('shows fields only when they apply', () => {
    const keys = (engine: Parameters<typeof fieldsFor>[0], settings: Record<string, string | number | boolean>) => fieldsFor(engine, { ...defaultSettings(engine), ...settings }).map(field => field.key)
    expect(keys('oracle', { connect_by: 'sid' })).toContain('sid')
    expect(keys('oracle', { connect_by: 'sid' })).not.toContain('service_name')
    expect(keys('oracle', { connect_by: 'descriptor' })).not.toContain('host')
    expect(keys('sqlserver', { auth: 'entra_service_principal' })).toEqual(expect.arrayContaining(['tenant_id', 'client_id', 'client_secret']))
    expect(keys('sqlserver', { auth: 'entra_service_principal' })).not.toContain('password')
    expect(keys('postgresql', { ssl_mode: 'verify-full' })).toContain('ca_certificate')
    expect(keys('postgresql', { ssl_mode: 'require' })).not.toContain('ca_certificate')
    expect(keys('mysql', { ssh: true })).toEqual(expect.arrayContaining(['ssh_host', 'ssh_private_key']))
  })

  it('checks hosts, ports, certificates and required secrets', () => {
    const settings = { ...defaultSettings('postgresql'), host: 'db.example.net', database: 'cases', username: 'formalie_app' }
    expect(checkConfig('postgresql', settings, { password: 'x' })).toEqual({})
    expect(checkConfig('postgresql', settings, {})).toEqual({ password: 'required' })
    expect(checkConfig('postgresql', settings, {}, ['password'])).toEqual({})
    expect(checkConfig('postgresql', { ...settings, host: 'localhost' }, { password: 'x' })).toEqual({ host: 'host_blocked' })
    expect(checkConfig('postgresql', { ...settings, host: 'db example' }, { password: 'x' })).toEqual({ host: 'host' })
    expect(checkConfig('postgresql', { ...settings, port: 70000 }, { password: 'x' })).toEqual({ port: 'port' })
    expect(checkConfig('postgresql', { ...settings, ssl_mode: 'verify-ca' }, { password: 'x', ca_certificate: 'nope' })).toEqual({ ca_certificate: 'pem' })
  })

  it('blocks loopback and metadata addresses but allows private networks', () => {
    for (const host of ['localhost', '127.0.0.1', '169.254.169.254', '::1', '0.0.0.0', 'metadata.google.internal']) expect(isBlockedHost(host), host).toBe(true)
    for (const host of ['10.0.0.5', 'db.example.net', '192.168.1.20']) expect(isBlockedHost(host), host).toBe(false)
  })

  it('keeps only known settings and the secrets in use', () => {
    const settings = cleanSettings('mysql', { host: ' db.example.net ', port: '3307', evil: 'x' } as never)
    expect(settings).toMatchObject({ host: 'db.example.net', port: 3307 })
    expect(settings).not.toHaveProperty('evil')
    expect(cleanSecrets('mysql', settings, { password: 'p', ssh_private_key: 'k', other: 'x' })).toEqual({ password: 'p' })
  })

  it('describes the address and database', () => {
    expect(addressOf('sqlserver', { ...defaultSettings('sqlserver'), host: 'sql.example.net', instance: 'HR' })).toBe('sql.example.net\\HR:1433')
    const descriptor = '(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=ora.example.net)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=FIN)))'
    expect(addressOf('oracle', { ...defaultSettings('oracle'), connect_by: 'descriptor', descriptor })).toBe('ora.example.net:2484')
    expect(databaseNameOf('oracle', { ...defaultSettings('oracle'), connect_by: 'descriptor', descriptor })).toBe('FIN')
  })
})

describe('permissions', () => {
  it('always needs Formalie’s own tables; the other tables follow the choice', () => {
    expect(levelsFor(ownOnly)).toEqual(['own'])
    expect(levelsFor(readOnly)).toEqual(['own', 'read'])
    expect(levelsFor(full)).toEqual(['own', 'read', 'write'])
    expect(operationsFor('mysql', ownOnly).filter(op => op.needed).map(op => op.key)).toEqual(['connect', 'create_table', 'own_rows', 'alter_table', 'create_index', 'cancel'])
    expect(operationsFor('mysql', full).map(op => op.key)).not.toContain('sequences')
    expect(operationsFor('postgresql', full).map(op => op.key)).toContain('sequences')
  })

  it('keeps Formalie’s tables apart where the engine allows', () => {
    const settings = (engine: Parameters<typeof tablesSchemaOf>[0], extra: Record<string, string> = {}) => ({ ...defaultSettings(engine), username: 'app', database: 'leads', ...extra })
    expect(tablesSchemaOf('postgresql', settings('postgresql'), full)).toBe('public')
    expect(tablesSchemaOf('postgresql', settings('postgresql'), { ...full, tables_schema: 'forms' })).toBe('forms')
    expect(tablesSchemaOf('sqlserver', settings('sqlserver'), full)).toBe('formalie')
    expect(tablesSchemaOf('oracle', settings('oracle'), full)).toBe('APP')
    expect(tablesSchemaOf('mysql', settings('mysql'), full)).toBe('leads')
  })

  it('writes a grant script per engine with the connection’s own names', () => {
    const script = (engine: Parameters<typeof grantScript>[0], settings: Record<string, string | number | boolean>, access = full, options = {}) => grantScriptText(grantScript(engine, { ...defaultSettings(engine), ...settings }, access, options))
    const mysql = script('mysql', { database: 'leads', username: 'app' }, ownOnly)
    expect(mysql).toContain("CREATE USER 'app'@'%'")
    expect(mysql).toContain('GRANT CREATE, ALTER, INDEX, REFERENCES, SELECT, INSERT, UPDATE, DELETE ON `leads`.*')
    expect(script('mysql', { database: 'leads', username: 'app' }, { ...full, schemas: ['crm'] })).toContain('GRANT INSERT, UPDATE, DELETE ON `crm`.*')

    const pgOwn = script('postgresql', { database: 'cases', username: 'app' }, ownOnly)
    expect(pgOwn).toContain('GRANT USAGE, CREATE ON SCHEMA "public" TO "app";')
    expect(pgOwn).not.toContain('SELECT ON ALL TABLES')
    const pg = script('postgresql', { database: 'cases', username: 'app' }, { ...full, tables_schema: 'formalie', schemas: ['public', 'intake'] })
    expect(pg).toContain('GRANT USAGE, CREATE ON SCHEMA "formalie"')
    expect(pg).toContain('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA "intake"')

    const sql = script('sqlserver', { database: 'People', username: 'app' }, readOnly)
    expect(sql).toContain('CREATE SCHEMA [formalie] AUTHORIZATION [app];')
    expect(sql).toContain('GRANT SELECT, VIEW DEFINITION ON SCHEMA::[dbo] TO [app];')
    expect(sql).not.toContain('GRANT INSERT')
    expect(script('sqlserver', { database: 'People', auth: 'entra_service_principal', client_id: 'abc' }, readOnly)).toContain('FROM EXTERNAL PROVIDER')

    expect(script('oracle', { schema: 'finance', username: 'app' }, full, { oracle23: true })).toContain('GRANT SELECT ANY TABLE ON SCHEMA "FINANCE" TO "APP";')
    const oracle19 = script('oracle', { schema: 'finance', username: 'app' }, full)
    expect(oracle19).toContain("FROM all_sequences WHERE sequence_owner = 'FINANCE'")
    expect(oracle19).toContain('GRANT CREATE TABLE, CREATE SEQUENCE TO "APP";')
  })

  it('quotes names safely', () => {
    const text = grantScriptText(grantScript('mysql', { ...defaultSettings('mysql'), database: 'a`b', username: "o'k" }, ownOnly))
    expect(text).toContain('`a``b`')
    expect(text).toContain("'o''k'@'%'")
  })
})

describe('data source labels', () => {
  const en = JSON.parse(readFileSync(join(__dirname, '../../i18n/locales/en.json'), 'utf8'))
  const ds = en.dataSources

  it('labels every field and every choice of every engine', () => {
    for (const engine of DB_ENGINES)
      for (const field of ENGINE_FIELDS[engine]) {
        expect(ds.field[field.key], `${engine}.${field.key}`).toBeTruthy()
        for (const option of field.options ?? []) expect(ds.option[field.key]?.[option], `${field.key}.${option}`).toBeTruthy()
      }
  })

  it('labels every operation, level, test step and finding', () => {
    for (const operation of DB_OPERATIONS) expect([ds.op[operation.key]?.label, ds.op[operation.key]?.uses].every(Boolean), operation.key).toBe(true)
    for (const level of ['own', 'read', 'write']) expect(ds.level[level] && ds.levelDesc[level] && ds.grant.block[level]).toBeTruthy()
    for (const step of TEST_STEPS) expect(ds.step[step] && ds.stepDesc[step], step).toBeTruthy()
    for (const finding of ['tls_off', 'trust_certificate', 'missing_permissions']) expect(ds.finding[finding]?.title, finding).toBeTruthy()
    for (const engine of DB_ENGINES) expect(ds.engineDesc[engine] && ds.access.tablesSchemaDesc[engine], engine).toBeTruthy()
    for (const other of ['none', 'read', 'read_write']) expect(ds.access.other[other] && ds.access.otherDesc[other] && ds.access.short[other], other).toBeTruthy()
  })

  it('labels every note a grant script can carry', () => {
    for (const engine of DB_ENGINES)
      for (const oracle23 of [true, false])
        for (const access of [ownOnly, readOnly, full])
          for (const block of grantScript(engine, defaultSettings(engine), access, { oracle23 })) for (const note of block.notes) expect(ds.grant.note[note], note).toBeTruthy()
  })
})

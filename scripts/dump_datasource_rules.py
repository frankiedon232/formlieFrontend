"""Records the frontend's data source rules (B9) into tests/vectors/datasource_rules.json: each engine's fields for
many settings, defaults, cleaning, field checks, addresses, database and schema names, encryption, blocked hosts,
and the operations a connection needs (shared/utils/datasources/engines.ts, permissions.ts).

    fmly\\Scripts\\python.exe scripts\\dump_datasource_rules.py [path\\to\\formalieFrontend]

tests/parity/test_datasource_rules.py holds the port (app/modules/data_sources/engines.py) to these answers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dump_frontend_rules import ROOT, run_in_node  # noqa: E402

OUT = ROOT / "tests" / "vectors" / "datasource_rules.json"

ENTRY = r"""
import * as E from '__SHARED__/utils/datasources/engines.ts'
import * as P from '__SHARED__/utils/datasources/permissions.ts'

const engines = ['mysql', 'mariadb', 'postgresql', 'sqlserver', 'oracle']
const PEM = '-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----'
const variants = [
  {}, { ssh: true }, { ssh: 'true' }, { ssl_mode: 'verify_ca' }, { ssl_mode: 'verify-full' }, { ssl_mode: 'disabled' }, { ssl_mode: 'disable' },
  { auth: 'entra_service_principal' }, { encrypt: 'optional' }, { encrypt: 'strict' }, { connect_by: 'sid' }, { connect_by: 'descriptor' },
  { protocol: 'tcp' }, { protocol: 'tcp', network_encryption: 'requested' }, { connect_by: 'descriptor', protocol: 'tcp' },
]
const values = {
  host: ['db.example.net', 'localhost', '127.0.0.1', '10.0.0.5', '999.1.1.1', '-bad.com', 'a_b.com', '[::1]', 'fe80::1', '169.254.169.254', '100.64.0.1',
    '224.0.0.1', 'metadata.google.internal', 'x.localhost', 'db.example.net.', '  spaced.example  ', '', 'ä.com', '::ffff:127.0.0.1', '0.0.0.0', '192.168.1.10'],
  port: [5432, '5432', 0, 65536, 3.5, 'abc', '', ' 22 ', '1e3', true],
  connect_timeout: [10, 0, 121, 120, '30', 2.5],
  database: ['cases', '', '  ', 'x'.repeat(200)],
  username: ['formalie_app', '', null],
  instance: ['PROD01', 'Prod_01$#@ .-', '9bad', '_ok', 'Ñame', 'x'.repeat(129)],
  sid: ['ORCL', '1abc'],
  tenant_id: ['3f2504e0-4f89-11d3-9a0c-0305e82c3301', 'nope', '3F2504E0-4F89-11D3-9A0C-0305E82C3301'],
}
const secretsCases = [{}, { password: 'pw' }, { password: '  ' }, { password: 'pw', ca_certificate: PEM, ssh_private_key: 'notpem', client_secret: 's', extra: 'x' }, { ssh_private_key: PEM, ssh_passphrase: 'p' }]

const fields = [], checks = [], cleaned = [], secrets = [], names = []
for (const engine of engines) {
  for (const variant of variants) {
    const settings = { ...E.defaultSettings(engine), ...variant }
    fields.push({ engine, settings, keys: E.fieldsFor(engine, settings).map(f => f.key), server: E.fieldsFor(engine, settings, 'server').map(f => f.key) })
    for (const s of secretsCases) {
      secrets.push({ engine, settings, secrets: s, clean: E.cleanSecrets(engine, settings, s) })
      checks.push({ engine, settings, secrets: s, kept: [], problems: E.checkConfig(engine, settings, s) })
      checks.push({ engine, settings, secrets: s, kept: ['password', 'ca_certificate'], problems: E.checkConfig(engine, settings, s, ['password', 'ca_certificate']) })
    }
    names.push({ engine, settings, address: E.addressOf(engine, settings), database: E.databaseNameOf(engine, settings), schema: E.defaultSchemaOf(engine, settings), encrypted: E.isEncrypted(engine, settings) })
  }
  for (const [key, list] of Object.entries(values)) for (const value of list) {
    const settings = { ...E.defaultSettings(engine), [key]: value }
    checks.push({ engine, settings, secrets: { password: 'pw' }, kept: [], problems: E.checkConfig(engine, settings, { password: 'pw' }) })
    checks.push({ engine, settings, secrets: {}, kept: [], step: 'server', problems: E.checkConfig(engine, settings, {}, [], 'server') })
  }
  const messy = { host: '  db.example.net ', port: '6000', ssh: 'true', ssh_port: 'abc', multi_subnet_failover: 'yes', unknown: 1, database: 12, username: null, password: 'secret', connect_timeout: 2.5 }
  cleaned.push({ engine, input: messy, settings: E.cleanSettings(engine, messy) })
  cleaned.push({ engine, input: {}, settings: E.cleanSettings(engine, {}) })
  names.push(...[{ host: 'h', port: 1, instance: 'I' }, { connect_by: 'descriptor', descriptor: '(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)(HOST=db.example.net)(PORT=2484))(CONNECT_DATA=(SERVICE_NAME=FINPDB1)))' },
    { connect_by: 'descriptor', descriptor: 'nothing' }, { connect_by: 'sid', sid: 'ORCL' }, { username: 'fin_app' }, { host: '', port: 5 }]
    .map(settings => ({ engine, settings, address: E.addressOf(engine, settings), database: E.databaseNameOf(engine, settings), schema: E.defaultSchemaOf(engine, settings), encrypted: E.isEncrypted(engine, settings) })))
}
const accesses = [P.DEFAULT_ACCESS, { ...P.DEFAULT_ACCESS, other: 'read' }, { ...P.DEFAULT_ACCESS, other: 'none', tables_schema: 'forms' }]
const operations = engines.flatMap(engine => accesses.map(access => ({ engine, access, ops: P.operationsFor(engine, access).map(o => ({ key: o.key, level: o.level, needed: o.needed })),
  levels: P.levelsFor(access), has: P.hasTablesSchema(engine), schema: P.tablesSchemaOf(engine, { database: 'db', username: 'App' }, access) })))
const blocked = values.host.map(host => ({ host, blocked: E.isBlockedHost(host) }))
const defaults = engines.map(engine => ({ engine, settings: E.defaultSettings(engine) }))
process.stdout.write(JSON.stringify({ about: 'Recorded from the frontend by scripts/dump_datasource_rules.py. Do not edit.', defaults, fields, checks, cleaned, secrets, names, operations, blocked }))
"""


def main() -> None:
    result = run_in_node(ENTRY, {})
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(result['checks'])} checks, {len(result['fields'])} field sets")


if __name__ == "__main__":
    main()

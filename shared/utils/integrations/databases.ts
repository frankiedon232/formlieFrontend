/**
 * Customer databases Formalie connects to (F12 Data sources; 00-OVERVIEW → Responses →
 * Destinations). Launch set; the alternative is Formalie's own encrypted storage. Each engine's
 * own connection settings live in shared/utils/datasources/engines.ts, the permissions it needs
 * in shared/utils/datasources/permissions.ts.
 */
export type DbEngine = 'mysql' | 'mariadb' | 'oracle' | 'postgresql' | 'sqlserver'

export interface SupportedDatabase {
  key: DbEngine
  name: string
  defaultPort: number
  /** Monochrome brand mark (simple-icons, drawn in the ink colour). */
  icon: string
}

export const SUPPORTED_DATABASES: SupportedDatabase[] = [
  { key: 'mysql', name: 'MySQL', defaultPort: 3306, icon: 'i-simple-icons-mysql' },
  { key: 'mariadb', name: 'MariaDB', defaultPort: 3306, icon: 'i-simple-icons-mariadb' },
  { key: 'oracle', name: 'Oracle', defaultPort: 1521, icon: 'i-simple-icons-oracle' },
  { key: 'postgresql', name: 'PostgreSQL', defaultPort: 5432, icon: 'i-simple-icons-postgresql' },
  { key: 'sqlserver', name: 'SQL Server', defaultPort: 1433, icon: 'i-simple-icons-microsoftsqlserver' },
]

export const DB_ENGINES = SUPPORTED_DATABASES.map(db => db.key)
export const databaseOf = (engine: string) => SUPPORTED_DATABASES.find(db => db.key === engine)

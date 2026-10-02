/**
 * Customer databases a form's responses can be written to (00-OVERVIEW → Responses → Destinations).
 * Launch set; the alternative is Formalie's own encrypted storage. Used by the sign-in showcase
 * and, in F11, by Integrations → Destinations.
 */
export interface SupportedDatabase {
  key: 'mysql' | 'mariadb' | 'oracle' | 'postgresql' | 'sqlserver'
  name: string
  defaultPort: number
}

export const SUPPORTED_DATABASES: SupportedDatabase[] = [
  { key: 'mysql', name: 'MySQL', defaultPort: 3306 },
  { key: 'mariadb', name: 'MariaDB', defaultPort: 3306 },
  { key: 'oracle', name: 'Oracle', defaultPort: 1521 },
  { key: 'postgresql', name: 'PostgreSQL', defaultPort: 5432 },
  { key: 'sqlserver', name: 'SQL Server', defaultPort: 1433 },
]

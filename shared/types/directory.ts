/** People and groups a field can be restricted to (field access, `field.audience`). */
export interface DirectoryItem {
  id: string
  name: string
  /** E-mail for people; the code for departments and job titles. */
  detail?: string
  /** Archived in Settings: kept so forms that still use it can name it. */
  archived?: boolean
}

export interface Directory {
  departments: DirectoryItem[]
  job_titles: DirectoryItem[]
  roles: DirectoryItem[]
  users: DirectoryItem[]
}

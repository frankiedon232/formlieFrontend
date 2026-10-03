/** People and groups a field can be restricted to (field access, `field.audience`). */
export interface DirectoryItem {
  id: string
  name: string
  /** E-mail for people; empty for departments and roles. */
  detail?: string
}

export interface Directory {
  departments: DirectoryItem[]
  roles: DirectoryItem[]
  users: DirectoryItem[]
}

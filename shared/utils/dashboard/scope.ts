// Dashboard forms filter (F21 M5), shared by the Workspace and Forms views of GET /dashboard.

/** The forms filter (F21 M5): `folder` (a folder id, or `none` for forms in no folder) and `owner` (a person's id). */
export function scopeFrom(query: Record<string, unknown>) {
  const folder = typeof query.folder === 'string' && query.folder ? query.folder : null
  const owner = typeof query.owner === 'string' && query.owner ? query.owner : null
  return {
    filtered: !!(folder || owner),
    matches: (form: { folder: { id: string } | null; owner: { id: string } }) => (!folder || (form.folder?.id ?? 'none') === folder) && (!owner || form.owner.id === owner),
  }
}

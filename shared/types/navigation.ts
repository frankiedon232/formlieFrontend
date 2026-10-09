/** GET /navigation/counts, the numbers and short lists next to sidebar items (docs/API-CONTRACT.md → Navigation). */
export interface NavCounts {
  /** `all` excludes archived forms, like the forms list. */
  forms: { all: number; draft: number; published: number; closed: number; archived: number; trash: number }
  /** Responses by review status; `new` = nobody has opened them yet. */
  responses: { all: number; new: number; reviewed: number; approved: number; rejected: number }
  /** Most recently used templates (by the forms made from them), then the most popular, up to 6. */
  /** Formalie templates (total), the workspace's own, and the categories most used first. */
  templates: { total: number; mine: number; categories: { key: string; count: number }[] }
  /** Most recently updated saved themes, up to 6. */
  /** Themes by kind (owner, 2026-10-03: the menu lists kinds, not every saved theme). */
  themes: { total: number; system: number; saved: number; created: number }
  pages: { total: number; system: number; saved: number; created: number }
  /** Folders for the sidebar (name, colour, forms this person can see), A to Z. */
  folders: { id: string; name: string; color: string | null; count: number }[]
  /** Data sources (F12): connections by status. */
  datasources: { total: number; connected: number; attention: number; failing: number; disabled: number; untested: number }
  /** Response storage (F12 M2): forms storing in a database, and how many are failing. */
  destinations: { total: number; failing: number }
  /** People area (F16): people by status, and the profiling lists (departments, job titles in use). Zeros for members. */
  people: { total: number; active: number; invited: number; pending: number; not_activated: number; disabled: number; departments: number; job_titles: number }
}

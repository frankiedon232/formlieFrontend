/** GET /navigation/counts — the numbers and short lists next to sidebar items (docs/API-CONTRACT.md → Navigation). */
export interface NavCounts {
  /** `all` excludes archived forms, like the forms list. */
  forms: { all: number; draft: number; published: number; closed: number; trash: number }
  /** Responses by review status; `new` = nobody has opened them yet. */
  responses: { all: number; new: number; reviewed: number; approved: number; rejected: number }
  /** Most recently used templates (by the forms made from them), then the most popular — up to 6. */
  /** Formalie templates (total), the workspace's own, and the categories most used first. */
  templates: { total: number; mine: number; categories: { key: string; count: number }[] }
  /** Most recently updated saved themes — up to 6. */
  /** Themes by kind (owner, 2026-10-03: the menu lists kinds, not every saved theme). */
  themes: { total: number; system: number; saved: number; created: number }
}

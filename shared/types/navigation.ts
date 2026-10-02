/** GET /navigation/counts — the numbers next to sidebar items (docs/API-CONTRACT.md → Navigation). */
export interface NavCounts {
  /** `all` excludes archived forms, like the forms list. */
  forms: { all: number; draft: number; published: number; closed: number }
  /** Responses nobody has opened yet. */
  responses: { new: number }
}

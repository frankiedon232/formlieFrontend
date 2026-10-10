/**
 * Data residency (F14, leftovers L7, owner 2026-10-10): the region a workspace's data lives in (responses, files,
 * backups, response emails, logs). Every workspace starts in Formalie's default region; another region is an
 * Enterprise service, set up by the Formalie team (the move is a migration, never a switch in the app). The
 * regions offered are infrastructure: the platform serves the real list, this one is the starting set.
 */
export const DATA_REGIONS = ['default', 'eu', 'uk', 'us', 'ca', 'au', 'in', 'sg', 'br'] as const
export type DataRegion = (typeof DATA_REGIONS)[number]

/** GET /settings/data-region */
export interface DataRegionInfo {
  region: DataRegion
  /** Regions Formalie can offer. */
  regions: DataRegion[]
  /** The plan includes choosing a region (Enterprise). */
  residency: boolean
}

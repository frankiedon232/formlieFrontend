/**
 * Where a workspace's data lives (F14, leftovers L7; docs/API-CONTRACT.md → Settings). Every workspace starts in
 * Formalie's default region; another one is an Enterprise service set up by the Formalie team in the platform
 * admin (a migration, never a switch here), so the portal only reads it. Kept in `.data/mock/regions.json`.
 *
 *   GET /settings/data-region → DataRegionInfo (settings.view)
 */
import { DATA_REGIONS, type DataRegion, type DataRegionInfo } from '#shared/utils/platform/regions'
import { requireAuth } from '../core/auth'
import { hasFeature } from '../core/plan'
import { loadPersisted } from '../core/persist'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { permissionsOf } from '../data/rolesStore'

/** Set by the platform admin; the mock reads what is there. */
const regions = new Map<string, DataRegion>(Object.entries(loadPersisted<Record<string, DataRegion>>('regions', {})))

export const getDataRegion = defineMockRoute(({ event }) => {
  const { tenant, user } = requireAuth(event)
  if (!permissionsOf(user, tenant).has('settings.view')) throw new MockError('FRM-PERM-1001')
  const result: DataRegionInfo = { region: regions.get(tenant.id) ?? 'default', regions: [...DATA_REGIONS], residency: hasFeature(tenant, 'data_residency') }
  return ok(result)
})

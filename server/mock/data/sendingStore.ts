/**
 * Where a workspace's emails come from, in the mock (Settings → Emails → Sending address, owner 2026-10-10),
 * kept in `.data/mock/sending.json`: Formalie's address, the workspace's own address on a verified domain,
 * or its own mail server. The mail server password stays here only (the backend keeps it encrypted).
 */
import type { SendingDomain, SendingMode, SmtpServer } from '#shared/types/emails'
import { loadPersisted, savePersisted } from '../core/persist'
import type { MockTenant } from './tenants'

export const FORMALIE_ADDRESS = 'no-reply@formalie.com'

export interface StoredSending {
  mode: SendingMode
  domain: SendingDomain | null
  smtp: (SmtpServer & { password: string | null }) | null
}

const stores = new Map<string, StoredSending>(Object.entries(loadPersisted<Record<string, StoredSending>>('sending', {})))
const save = () => savePersisted('sending', () => Object.fromEntries(stores))

export function sendingOf(tenant: MockTenant): StoredSending {
  let sending = stores.get(tenant.id)
  if (!sending) {
    sending = { mode: 'formalie', domain: null, smtp: null }
    stores.set(tenant.id, sending)
  }
  return sending
}

export function updateSending(tenant: MockTenant, change: (sending: StoredSending) => void) {
  const sending = sendingOf(tenant)
  change(sending)
  // Never keep sending from something that stopped working
  if (sending.mode === 'domain' && sending.domain?.status !== 'verified') sending.mode = 'formalie'
  if (sending.mode === 'smtp' && sending.smtp?.status !== 'working') sending.mode = 'formalie'
  save()
  return sending
}

/** The address the workspace's emails go out from right now. */
export function fromAddress(tenant: MockTenant): string {
  const sending = sendingOf(tenant)
  if (sending.mode === 'domain' && sending.domain?.status === 'verified') return sending.domain.address
  if (sending.mode === 'smtp' && sending.smtp?.status === 'working') return sending.smtp.from_address
  return FORMALIE_ADDRESS
}

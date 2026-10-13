/**
 * After Paddle's checkout window completes or closes (owner 2026-10-13, Paddle is the payment provider): the browser
 * never decides that something was paid. Only Paddle's signed notification to the backend completes a checkout, so
 * the portal asks GET /billing/checkout/{id} until it is no longer open, every 2 seconds for about a minute.
 */
import type { CheckoutStatus } from '#shared/types/billing'

export const CHECKOUT_POLL_EVERY_MS = 2_000
export const CHECKOUT_POLL_FOR_MS = 60_000

const pause = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms))

/**
 * Reads the checkout's status until it is completed, cancelled or expired, or the time is up (then `open`: the
 * payment is still being confirmed). A failed read counts as still open and is tried again.
 */
export async function waitForCheckout(
  read: () => Promise<CheckoutStatus>,
  options: { everyMs?: number; forMs?: number; sleep?: (ms: number) => Promise<void> } = {},
): Promise<CheckoutStatus> {
  const every = options.everyMs ?? CHECKOUT_POLL_EVERY_MS
  const tries = Math.max(1, Math.floor((options.forMs ?? CHECKOUT_POLL_FOR_MS) / every))
  const sleep = options.sleep ?? pause
  for (let attempt = 0; attempt < tries; attempt++) {
    if (attempt) await sleep(every)
    try {
      const status = await read()
      if (status !== 'open') return status
    } catch {
      // A hiccup while Paddle's notification is on its way: ask again
    }
  }
  return 'open'
}

/** A checkout's status now: sessions saved before statuses existed count as open; an open one past its time has expired. */
export function checkoutStatusOf(session: { status?: CheckoutStatus; expires_at: string }, now = Date.now()): CheckoutStatus {
  const status = session.status ?? 'open'
  return status === 'open' && Date.parse(session.expires_at) < now ? 'expired' : status
}

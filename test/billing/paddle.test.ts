import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { CHECKOUT_POLL_EVERY_MS, CHECKOUT_POLL_FOR_MS, checkoutStatusOf, waitForCheckout } from '../../shared/utils/billing/checkout'
import type { CheckoutStatus } from '../../shared/types/billing'
import { contentSecurityPolicy, PADDLE_FRAMES, securityHeaders } from '../../edge/security-headers'

const noWait = async () => {}

describe('after Paddle\'s window: the backend decides, never the browser', () => {
  it('asks every 2 seconds for about a minute', () => {
    expect(CHECKOUT_POLL_EVERY_MS).toBe(2_000)
    expect(CHECKOUT_POLL_FOR_MS).toBe(60_000)
  })
  it('stops once Paddle\'s notification has completed it', async () => {
    const answers: CheckoutStatus[] = ['open', 'open', 'completed']
    let reads = 0
    const waits: number[] = []
    const status = await waitForCheckout(async () => answers[reads++]!, { sleep: async ms => void waits.push(ms) })
    expect(status).toBe('completed')
    expect(reads).toBe(3)
    expect(waits).toEqual([2_000, 2_000])
  })
  it('answers open (still being confirmed) when a minute passes without it', async () => {
    let reads = 0
    const status = await waitForCheckout(async () => (reads++, 'open'), { sleep: noWait })
    expect(status).toBe('open')
    expect(reads).toBe(30)
  })
  it('tries again after a failed read', async () => {
    let reads = 0
    const status = await waitForCheckout(async () => {
      reads++
      if (reads === 1) throw new Error('network')
      return 'completed'
    }, { sleep: noWait })
    expect(status).toBe('completed')
  })
  it('takes a short look only when the window closed without paying', async () => {
    let reads = 0
    await waitForCheckout(async () => (reads++, 'open'), { forMs: 6_000, sleep: noWait })
    expect(reads).toBe(3)
  })
  it('passes on a cancelled or expired checkout at once', async () => {
    expect(await waitForCheckout(async () => 'cancelled', { sleep: noWait })).toBe('cancelled')
    expect(await waitForCheckout(async () => 'expired', { sleep: noWait })).toBe('expired')
  })
})

describe('a checkout\'s status in the mock', () => {
  const now = Date.parse('2026-10-13T12:00:00Z')
  it('reads older saved sessions as open, and open ones past their time as expired', () => {
    expect(checkoutStatusOf({ expires_at: '2026-10-13T12:30:00Z' }, now)).toBe('open')
    expect(checkoutStatusOf({ status: 'open', expires_at: '2026-10-13T11:59:00Z' }, now)).toBe('expired')
    expect(checkoutStatusOf({ status: 'completed', expires_at: '2026-10-13T11:59:00Z' }, now)).toBe('completed')
    expect(checkoutStatusOf({ status: 'cancelled', expires_at: '2026-10-13T12:30:00Z' }, now)).toBe('cancelled')
  })
})

describe('security headers let Paddle\'s checkout work', () => {
  const headers = securityHeaders(true)
  it('loads Paddle.js from Paddle\'s CDN only', () => {
    const script = contentSecurityPolicy().split('; ').find(directive => directive.startsWith('script-src '))!
    expect(script).toBe("script-src 'self' 'unsafe-inline' https://cdn.paddle.com")
  })
  it('lets Paddle\'s checkout frames in', () => {
    expect(contentSecurityPolicy()).toContain("frame-src 'self' https:")
    expect(PADDLE_FRAMES).toEqual(['https://buy.paddle.com', 'https://sandbox-buy.paddle.com'])
  })
  it('allows card wallets only in Formalie and Paddle\'s frames', () => {
    expect(headers['Permissions-Policy']).toContain('payment=(self "https://buy.paddle.com" "https://sandbox-buy.paddle.com")')
    expect(headers['Permissions-Policy']).toContain('camera=()')
  })
  it('keeps PayPal\'s pop-up linked to Paddle\'s window', () => {
    expect(headers['Cross-Origin-Opener-Policy']).toBe('same-origin-allow-popups')
  })
})

describe('texts', () => {
  const locales = join(__dirname, '../../i18n/locales')
  const files = readdirSync(locales).filter(file => file.endsWith('.json'))
  it('name Paddle, never Payoneer, in all 20 languages', () => {
    expect(files).toHaveLength(20)
    for (const file of files) {
      const raw = readFileSync(join(locales, file), 'utf8')
      expect(raw.toLowerCase(), file).not.toContain('payoneer')
      const billing = JSON.parse(raw).billing
      for (const text of [billing.card.secure, billing.checkout.desc, billing.checkout.secure]) expect(text, file).toContain('Paddle')
      for (const key of ['update', 'secure']) expect(billing.card[key], `${file} card.${key}`).toBeTruthy()
      for (const key of ['confirming', 'confirmingDesc', 'pending', 'pendingDesc', 'unavailable']) expect(billing.checkout[key], `${file} checkout.${key}`).toBeTruthy()
      for (const key of ['pdf', 'pdfMissing', 'pdfReady', 'pdfOpen']) expect(billing.invoice[key], `${file} invoice.${key}`).toBeTruthy()
      // The card can't be removed with Paddle: those texts are gone
      expect(billing.card.remove, file).toBeUndefined()
    }
  })
})

import { createHmac } from 'node:crypto'
import { describe, expect, it } from 'vitest'
import { checkWebhookUrl, signedPayload, webhookStatusOf, WEBHOOK_RETRY_MINUTES } from '../../shared/utils/integrations/webhooks'

describe('webhook addresses', () => {
  it('take public HTTPS addresses only', () => {
    expect(checkWebhookUrl('https://hooks.example.com/formalie')).toBeNull()
    expect(checkWebhookUrl('')).toBe('required')
    expect(checkWebhookUrl('not a url')).toBe('url')
    expect(checkWebhookUrl('http://hooks.example.com')).toBe('https')
    expect(checkWebhookUrl('https://user:pass@hooks.example.com')).toBe('url')
    expect(checkWebhookUrl('https://api.formalie.dev/x')).toBe('host')
    expect(checkWebhookUrl('https://acme.formalie.com/x')).toBe('host')
  })

  it('never call private networks, the machine itself or cloud metadata', () => {
    for (const url of ['https://10.0.0.5/hook', 'https://192.168.1.10/hook', 'https://172.20.0.1/hook', 'https://169.254.169.254/latest', 'https://127.0.0.1/hook', 'https://localhost/hook', 'https://[::1]/hook', 'https://metadata.google.internal/'])
      expect(checkWebhookUrl(url), url).toBe('private')
    expect(checkWebhookUrl('https://203.0.113.10/hook')).toBeNull()
  })

  it('let a local receiver through only while developing', () => {
    expect(checkWebhookUrl('http://localhost:2299/hook', { allowLocal: true })).toBeNull()
    expect(checkWebhookUrl('http://127.0.0.1:2299/hook', { allowLocal: true })).toBeNull()
    expect(checkWebhookUrl('http://10.0.0.5/hook', { allowLocal: true })).toBe('https')
  })
})

describe('deliveries', () => {
  it('are signed over the timestamp and the raw body', () => {
    const body = '{"type":"response.created"}'
    const signature = createHmac('sha256', 'formalie_hook_secret').update(signedPayload(1767225600, body)).digest('hex')
    expect(signedPayload(1767225600, body)).toBe(`1767225600.${body}`)
    expect(signature).toMatch(/^[0-9a-f]{64}$/)
  })

  it('retry five times and report a status', () => {
    expect(WEBHOOK_RETRY_MINUTES).toEqual([1, 5, 15, 60, 360])
    expect(webhookStatusOf({ enabled: true, consecutive_failures: 0 })).toBe('active')
    expect(webhookStatusOf({ enabled: true, consecutive_failures: 2 })).toBe('failing')
    expect(webhookStatusOf({ enabled: false, consecutive_failures: 0 })).toBe('paused')
  })
})

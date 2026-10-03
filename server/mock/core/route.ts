import type { H3Event } from 'h3'
import type { EnvelopeRequestPayload } from '#shared/types/crypto'
import {
  ENVELOPE_CONTENT_TYPE,
  ENVELOPE_HEADER,
  decodeEnvelopeHeader,
  isEnvelope,
  isEnvelopeFresh,
  openEnvelope,
  sealEnvelope,
} from '#shared/utils/crypto/envelope'
import { MockError, fail, type MockReply } from './respond'
import { decodeIds, decodeRouteParams, encodeIds } from './ids'
import { claimNonce, isCsrfTokenValid, useSessionKey } from './store'

export interface MockRouteContext {
  event: H3Event
  kid: string
  query: Record<string, unknown>
  body: unknown
}

interface MockRouteOptions {
  /** Plaintext endpoint (handshake, health). Everything else is enveloped. */
  plain?: boolean
}

const STATE_CHANGING = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

function sendPlain(event: H3Event, reply: MockReply) {
  setResponseStatus(event, reply.status)
  return reply.body
}

/** Full request path before `useBase` stripped the `/api/v1` prefix. */
function requestPath(event: H3Event): string {
  return (event.context.fullPath as string | undefined) ?? event.path.split('?')[0] ?? ''
}

/**
 * Wraps a mock handler with the server half of SECURITY-PROTOCOL.md:
 * envelope extraction, key lookup, freshness, replay, integrity,
 * method/path binding, CSRF on state-changing requests, encrypted reply.
 */
export function defineMockRoute(
  handler: (ctx: MockRouteContext) => MockReply | Promise<MockReply>,
  options: MockRouteOptions = {},
) {
  return defineEventHandler(async event => {
    const method = event.method.toUpperCase()

    if (options.plain) {
      try {
        const body = method === 'GET' ? null : await readBody(event)
        return sendPlain(event, await handler({ event, kid: '', query: getQuery(event), body }))
      } catch (error) {
        return sendPlain(
          event,
          error instanceof MockError ? fail(error.code, error.details) : fail('FRM-GEN-5000'),
        )
      }
    }

    const envelope =
      method === 'GET' || method === 'DELETE'
        ? decodeEnvelopeHeader(getHeader(event, ENVELOPE_HEADER) ?? '')
        : getHeader(event, 'content-type')?.startsWith(ENVELOPE_CONTENT_TYPE)
          ? await readBody(event).catch(() => null)
          : null

    if (!isEnvelope(envelope)) return sendPlain(event, fail('FRM-SEC-1001'))

    const session = useSessionKey(envelope.kid)
    // Unknown key: we cannot encrypt the reply, so this one stays plaintext.
    if (!session) return sendPlain(event, fail('FRM-SEC-1004'))

    // Real ids never leave the server: every id in the reply becomes an encrypted reference (core/ids.ts).
    const reply = async (result: MockReply) => {
      setResponseStatus(event, result.status)
      setHeader(event, 'content-type', ENVELOPE_CONTENT_TYPE)
      return sealEnvelope(session.key, envelope.kid, encodeIds(result.body))
    }

    if (!isEnvelopeFresh(envelope)) return reply(fail('FRM-SEC-1002'))
    if (!claimNonce(envelope.nonce)) return reply(fail('FRM-SEC-1003'))

    let payload: EnvelopeRequestPayload
    try {
      payload = await openEnvelope<EnvelopeRequestPayload>(session.key, envelope)
    } catch {
      return reply(fail('FRM-SEC-1005'))
    }

    if (payload.method?.toUpperCase() !== method || payload.path !== requestPath(event)) {
      return reply(fail('FRM-SEC-1005'))
    }

    if (STATE_CHANGING.has(method) && !isCsrfTokenValid(getHeader(event, 'x-csrf-token'), envelope.kid)) {
      return reply(fail('FRM-SEC-1006'))
    }

    // …and references coming in are turned back into the real ids before the route runs.
    decodeRouteParams(event.context.params)
    try {
      return reply(
        await handler({ event, kid: envelope.kid, query: decodeIds(payload.query ?? {}), body: decodeIds(payload.body) }),
      )
    } catch (error) {
      if (error instanceof MockError) return reply(fail(error.code, error.details))
      console.error('[mock-api]', error)
      return reply(fail('FRM-GEN-5000'))
    }
  })
}

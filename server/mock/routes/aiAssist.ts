/**
 * Mock AI assistant in the builder (F19 M3, docs/API-CONTRACT.md → AI assistant).
 *
 *   POST /ai/forms/:id/assist   { action (fields · help · logic · check), schema (the draft being edited) }
 *                               → AiAssistResult (ai.assist; the form must be editable; the assistant must
 *                               be allowed to read forms). The builder applies the suggestions it wants and
 *                               reports how many with POST /ai/requests/:id/apply { count }.
 */
import { z } from 'zod'
import { AI_ASSIST_ACTIONS, type AiAssistResult } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'
import { formSchemaV1 } from '#shared/utils/forms/schema'
import { assistForm } from '../ai/builderEngine'
import { requireAuth } from '../core/auth'
import { MockError, ok } from '../core/respond'
import { defineMockRoute } from '../core/route'
import { parseBody } from '../core/validate'
import { recordAiRequest, requireAi } from '../data/aiStore'
import { requireAction } from '../data/formPermissions'
import { formsOf } from '../data/formStore'

const input = z.object({ action: z.enum(AI_ASSIST_ACTIONS), schema: formSchemaV1 })
const TITLES = { fields: 'Suggest fields', help: 'Write help texts', logic: 'Add logic', check: 'Check my form' } as const

export const assistFormRoute = defineMockRoute(async ({ event, body }) => {
  const { tenant, user } = requireAuth(event)
  requireAi(tenant, 'builder', ['forms'])
  const form = formsOf(tenant).forms.find(item => item.id === getRouterParam(event, 'id') && !item.deleted_at)
  if (!form) throw new MockError('FRM-GEN-1004')
  requireAction(form, user, 'edit', tenant)
  const values = parseBody(input, body)
  await new Promise(resolve => setTimeout(resolve, 700))
  const suggestions = assistForm(values.action, values.schema, form.name)
  const request = recordAiRequest(tenant, user, {
    kind: 'builder',
    status: suggestions.length ? 'proposed' : 'discarded',
    title: TITLES[values.action],
    target: { type: 'form', id: form.id, name: form.name },
    credits: AI_KIND_META.builder.credits,
    prompt: TITLES[values.action],
    result: `${suggestions.length} suggestion${suggestions.length === 1 ? '' : 's'}.`,
    read: ['forms'],
    notes: [{ code: 'assist_found', params: { n: suggestions.length } }],
    output: { form_id: form.id, count: suggestions.length },
  })
  const result: AiAssistResult = { request_id: request.id, action: values.action, suggestions, credits: request.credits }
  return ok(result)
})

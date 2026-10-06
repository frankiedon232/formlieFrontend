<!--
  One method of an endpoint in the docs (F13 M5; redesigned in M7, owner 2026-10-06). A coloured
  header (method, address, what it does, Try it); then side by side on wide screens: on the left
  what can be sent (each question with its key, type, required and allowed values) or the query
  options, with the method's notes; on the right a dark code panel (five languages, Copy) and the
  answers it can give (success and the usual errors). Stacked on smaller screens.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'
import { exampleRecord } from '#shared/utils/apiService/endpoints'
import { CALL_HEADERS, endpointCalls, fieldSchema } from '#shared/utils/apiService/snippets'
import type { ApiMethod } from '#shared/utils/urls/public'

/** Every answer carries the token's expiry (the expiry tracker, owner 2026-10-06). */
const EXPIRY = { token_expires_at: '2027-01-01T00:00:00Z', token_expires_in_days: 87 }

const props = defineProps<{ endpoint: ApiEndpointDetail; method: ApiMethod }>()
const emit = defineEmits<{ try: [method: ApiMethod] }>()
const { t } = useI18n()
// The workspace's own token that may call it, masked, like the endpoint panel (owner, 2026-10-06)
const callers = useCallerToken()
void callers.load()
const token = computed(() => (callers.tokens.value ? callers.pick(props.endpoint, props.method) : null))
const call = computed(() => endpointCalls(props.endpoint, token.value?.preview).find(item => item.method === props.method)!)
const writes = computed(() => props.method === 'POST' || props.method === 'PUT')
const accepted = computed(() => props.endpoint.fields.filter(field => field.accept))
const filters = computed(() => props.endpoint.fields.filter(field => field.filter))
const typeOf = (field: ApiEndpointDetail['fields'][number]) => {
  const schema = fieldSchema(field)
  return schema.type === 'array' ? `${(schema.items as { type: string }).type}[]` : String(schema.format ?? schema.type)
}
const path = computed(() => `/${props.endpoint.name}${props.method === 'PUT' || props.method === 'DELETE' ? '/{id}' : ''}`)
const answers = computed(() => {
  const record = exampleRecord(props.endpoint.fields)
  const ok = props.method === 'GET' ? { status: 200, body: { data: [record], meta: { page: 1, per_page: Math.min(20, props.endpoint.page_size), total: 1, total_pages: 1, ...EXPIRY } } } : props.method === 'POST' ? { status: 201, body: { data: record, meta: EXPIRY } } : props.method === 'PUT' ? { status: 200, body: { data: record, meta: EXPIRY } } : { status: 200, body: { data: { id: record.id, deleted: true }, meta: EXPIRY } }
  const error = (status: number, code: string, details: unknown[] = []) => ({ status, body: { error: { code, message: '…', details } } })
  return [
    ok,
    error(401, 'FRM-API-1010'),
    ...(writes.value ? [error(422, 'FRM-RESP-1001', [{ field: accepted.value[0]?.key ?? 'email', message: 'required' }])] : []),
    ...(props.method === 'PUT' || props.method === 'DELETE' ? [error(404, 'FRM-API-1013')] : []),
    error(429, 'FRM-GEN-1029'),
  ]
})
const shownAnswer = ref(0)
watch(() => props.method, () => (shownAnswer.value = 0))
</script>

<template>
  <section class="overflow-hidden rounded-xl border border-default bg-default" :aria-label="`${method} ${path}`">
    <header class="relative flex flex-wrap items-center justify-between gap-3 border-b border-default px-4 py-3 ps-5 sm:px-5 sm:ps-6">
      <span class="absolute inset-y-0 start-0 w-1" :class="METHOD_BAR[method]" aria-hidden="true" />
      <div class="flex min-w-0 flex-col gap-0.5">
        <div class="flex min-w-0 items-center gap-2">
          <ApiMethods :methods="[method]" size="sm" />
          <code class="truncate font-mono text-sm font-semibold text-highlighted" dir="ltr">{{ path }}</code>
        </div>
        <p class="text-sm text-muted">{{ t(`apiService.wizard.method.${method}`) }}</p>
      </div>
      <UButton :label="t('apiService.docs.tryIt')" icon="i-lucide-play" color="neutral" size="sm" @click="emit('try', method)" />
    </header>

    <div class="grid lg:grid-cols-2">
      <div class="flex min-w-0 flex-col gap-4 p-4 sm:p-5">
        <template v-if="writes">
          <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">
            {{ t('apiService.docs.body') }}
          </h4>
          <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
            <li v-for="field in accepted" :key="field.key" class="flex flex-col gap-1 px-3 py-2.5">
              <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
                <code class="font-mono text-sm font-medium text-highlighted" dir="ltr">{{ field.key }}</code>
                <span class="font-mono text-xs text-muted">{{ typeOf(field) }}</span>
                <UBadge v-if="field.required && method === 'POST'" :label="t('apiService.fields.required')" color="error" variant="soft" size="xs" class="rounded-md" />
              </div>
              <p class="text-xs text-muted">{{ field.label }}</p>
              <div v-if="field.options?.length" class="flex flex-wrap gap-1">
                <code v-for="option in field.options.slice(0, 10)" :key="option.value" class="rounded bg-elevated px-1.5 py-0.5 font-mono text-[11px] text-highlighted" :title="option.label" dir="ltr">{{ option.value }}</code>
                <span v-if="field.options.length > 10" class="text-[11px] text-muted">+{{ field.options.length - 10 }}</span>
              </div>
              <p v-else-if="field.type === 'file_upload' || field.type === 'image_upload'" class="flex items-center gap-1 text-xs text-muted"><UIcon name="i-lucide-paperclip" class="size-3.5" />{{ t('apiService.docs.fileValue') }}</p>
            </li>
          </ul>
          <p v-if="method === 'PUT'" class="flex items-start gap-2 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('apiService.docs.putHint') }}</p>
          <p v-if="method === 'POST'" class="flex items-start gap-2 text-xs text-muted"><UIcon name="i-lucide-fingerprint" class="mt-0.5 size-3.5 shrink-0" />{{ t('apiService.docs.keyHint') }}</p>
        </template>

        <template v-if="method === 'GET'">
          <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">
            {{ t('apiService.docs.query') }}
          </h4>
          <ul class="flex flex-col divide-y divide-default rounded-lg border border-default">
            <li class="flex flex-col gap-0.5 px-3 py-2.5"><code class="font-mono text-sm font-medium text-highlighted">page</code><span class="text-xs text-muted">{{ t('apiService.docs.page') }}</span></li>
            <li class="flex flex-col gap-0.5 px-3 py-2.5"><code class="font-mono text-sm font-medium text-highlighted">per_page</code><span class="text-xs text-muted">{{ t('apiService.docs.perPage', { n: endpoint.page_size }) }}</span></li>
            <li class="flex flex-col gap-0.5 px-3 py-2.5"><code class="font-mono text-sm font-medium text-highlighted">sort=submitted_at</code><span class="text-xs text-muted">{{ t('apiService.docs.sort') }}</span></li>
            <li v-for="field in filters" :key="field.key" class="flex flex-col gap-0.5 px-3 py-2.5"><code class="font-mono text-sm font-medium text-highlighted" dir="ltr">{{ field.key }}=…</code><span class="text-xs text-muted">{{ t('apiService.docs.filterBy', { label: field.label }) }}</span></li>
          </ul>
          <p class="flex items-start gap-2 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('apiService.docs.oneHint') }}</p>
        </template>

        <p v-if="method === 'DELETE'" class="flex items-start gap-2 text-sm text-muted"><UIcon name="i-lucide-archive" class="mt-0.5 size-4 shrink-0" />{{ t('apiService.docs.deleteHint') }}</p>

        <div class="flex flex-col gap-1.5">
          <h4 class="text-xs font-semibold tracking-wide text-muted uppercase">
            {{ t('apiService.docs.headers') }}
          </h4>
          <div class="flex flex-wrap gap-1.5">
            <code v-for="header in CALL_HEADERS" :key="header" class="rounded-md border border-default px-2 py-0.5 font-mono text-xs text-highlighted" dir="ltr">{{ header }}</code>
          </div>
        </div>
      </div>

      <div class="flex min-w-0 flex-col gap-3 border-t border-default bg-neutral-950 p-4 text-neutral-100 sm:p-5 lg:border-s lg:border-t-0">
        <ApiDocsSnippets :call="call" dark />
        <p v-if="callers.tokens.value" class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-neutral-400">
          <UIcon name="i-lucide-key-round" class="size-3.5 shrink-0" />
          <template v-if="token">
            {{ t('apiService.call.tokenUsed') }}
            <ULink :to="{ path: '/api-service/auth', query: { token: token.id } }" class="font-medium text-neutral-100 underline-offset-2 hover:underline">{{ token.name }}</ULink>
            <span>{{ t('apiService.call.tokenWhere') }}</span>
          </template>
          <template v-else>
            {{ t('apiService.call.noToken') }}
            <ULink :to="{ path: '/api-service/auth', query: { new: '1', endpoint: endpoint.id } }" class="font-medium text-neutral-100 underline-offset-2 hover:underline">{{ t('apiService.call.makeToken') }}</ULink>
          </template>
        </p>
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center gap-1">
            <span class="me-2 text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">{{ t('apiService.call.answer') }}</span>
            <button
              v-for="(answer, i) in answers"
              :key="answer.status"
              type="button"
              class="rounded-md px-2 py-0.5 font-mono text-[11px] transition-colors focus-visible:outline-2 focus-visible:outline-neutral-400"
              :class="shownAnswer === i ? 'bg-neutral-800 text-white' : 'text-neutral-400 hover:text-neutral-200'"
              :aria-pressed="shownAnswer === i"
              @click="shownAnswer = i"
            >
              <span class="me-1 inline-block size-1.5 rounded-full align-middle" :class="answer.status < 300 ? 'bg-green-400' : answer.status === 429 ? 'bg-amber-400' : 'bg-red-400'" />{{ answer.status }}
            </button>
          </div>
          <pre class="max-h-80 overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-200" dir="ltr">{{ JSON.stringify(answers[shownAnswer]?.body, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </section>
</template>

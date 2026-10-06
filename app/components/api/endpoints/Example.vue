<!--
  What a call to an endpoint looks like (F13 M1), generated from its chosen fields: the method and
  address, the headers, the JSON body for POST / PUT and the JSON answer, each with Copy. Values are
  made up; the token is one of the workspace's own that may call it, masked, with a link to it in
  Tokens & headers (owner 2026-10-06), or a link to make one when none may.
-->
<script setup lang="ts">
import type { ApiEndpointField } from '#shared/types/apiService'
import { exampleRecord, exampleRequestBody } from '#shared/utils/apiService/endpoints'
import { NEW_KEY } from '#shared/utils/apiService/snippets'
import type { ApiMethod } from '#shared/utils/urls/public'

// Every answer carries the token's expiry (the expiry tracker, owner 2026-10-06)
const EXPIRY = { token_expires_at: '2027-01-01T00:00:00Z', token_expires_in_days: 87 }

const props = defineProps<{ methods: ApiMethod[]; url: string; fields: ApiEndpointField[]; pageSize: number; endpoint?: { id: string; service: { id: string } } | null }>()
const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()

const method = ref<ApiMethod>(props.methods[0] ?? 'POST')
watch(() => props.methods, list => !list.includes(method.value) && list[0] && (method.value = list[0]))
const tabs = computed(() => props.methods.map(item => ({ value: item, label: item })))
const json = (value: unknown) => JSON.stringify(value, null, 2)
const example = computed(() => {
  const record = exampleRecord(props.fields)
  const one = `${props.url}/${record.id}`
  switch (method.value) {
    case 'POST':
      return { line: `POST ${props.url}`, body: json(exampleRequestBody(props.fields)), status: '201 Created', answer: json({ data: record, meta: EXPIRY }) }
    case 'PUT':
      return { line: `PUT ${one}`, body: json(exampleRequestBody(props.fields)), status: '200 OK', answer: json({ data: record, meta: EXPIRY }) }
    case 'DELETE':
      return { line: `DELETE ${one}`, body: null, status: '200 OK', answer: json({ data: { id: record.id, deleted: true }, meta: EXPIRY }) }
    default:
      return { line: `GET ${props.url}?page=1&per_page=${Math.min(20, props.pageSize)}`, body: null, status: '200 OK', answer: json({ data: [record], meta: { page: 1, per_page: Math.min(20, props.pageSize), total: 1, ...EXPIRY } }) }
  }
})
// The headers a call sends (owner, 2026-10-06): Formalie-Key only on POST, where it is required
const callers = useCallerToken()
if (props.endpoint) void callers.load(true)
const token = computed(() => (props.endpoint && callers.tokens.value ? callers.pick(props.endpoint, method.value) : null))
// A client id and secret first get a short-lived token at /token (owner, 2026-10-06: two ways, never both)
const ACCESS = '<short-lived token from /token>'
const tokenStep = computed(() => {
  if (token.value?.kind !== 'client') return null
  const body = json({ client_id: token.value.client_id, client_secret: '<client secret>' })
  const answer = `{ "access_token": "…", "token_type": "Bearer", "expires_in": ${(token.value.lifetime_minutes ?? 15) * 60} }`
  return `POST ${props.url.replace(/\/[^/]+$/, '')}/token\nContent-Type: application/json\n\n${body}\n\n→ ${answer}`
})
const headers = computed(() => [`Authorization: Bearer ${token.value?.kind === 'client' ? ACCESS : (token.value?.preview ?? '<token>')}`, 'Content-Type: application/json', ...(method.value === 'POST' ? [`Formalie-Key: ${NEW_KEY}`] : [])].join('\n'))
function copyText(text: string) {
  void copy(text)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <UTabs v-if="methods.length > 1" v-model="method" :items="tabs" :content="false" color="neutral" size="xs" :ui="{ ...SEGMENTED_UI, label: 'font-mono' }" :aria-label="t('apiService.call.method')" />
    <AppEmpty v-if="!methods.length" size="xs" icon="i-lucide-route-off" :title="t('apiService.noMethods')" />
    <template v-else>
      <div v-if="tokenStep" class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-medium text-muted">{{ t('apiService.call.step1') }}</span>
          <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyText(tokenStep)" />
        </div>
        <pre class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-muted" dir="ltr">{{ tokenStep }}</pre>
      </div>
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-medium text-muted">{{ tokenStep ? t('apiService.call.step2') : t('apiService.call.request') }}</span>
          <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyText(`${example.line}\n${headers}${example.body ? `\n\n${example.body}` : ''}`)" />
        </div>
        <pre class="overflow-x-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-highlighted" dir="ltr"><span class="font-semibold">{{ example.line }}</span>
<span class="text-muted">{{ headers }}</span><template v-if="example.body">

{{ example.body }}</template></pre>
        <ApiCallToken v-if="endpoint && callers.tokens.value" :token="token" :endpoint-id="endpoint.id" />
      </div>
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between gap-2">
          <span class="text-xs font-medium text-muted">{{ t('apiService.call.answer') }} · <span class="font-mono">{{ example.status }}</span></span>
          <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyText(example.answer)" />
        </div>
        <pre class="max-h-72 overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ example.answer }}</pre>
      </div>
      <p class="text-xs text-muted">{{ t('apiService.call.note') }}</p>
    </template>
  </div>
</template>

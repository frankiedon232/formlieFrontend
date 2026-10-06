<!--
  Try it (F13 M5; a drawer since M7, owner 2026-10-06): one call to an endpoint through every real
  check, with a test token made for it (nothing is ever stored; not-live endpoints can be tried
  too). Left: the request, like an API client: the method (in its colour), the address with the
  record id in it, then Body or Headers (the token and Content-Type filled in and locked, a fresh
  Formalie-Key for each new POST that can be kept to see a retry, the endpoint's required headers).
  Right: the answer, its status, time and size, the JSON or its headers, and the last calls.
-->
<script setup lang="ts">
import type { ApiEndpointDetail, ApiTryResult } from '#shared/types/apiService'
import { exampleRequestBody } from '#shared/utils/apiService/endpoints'
import type { ApiMethod } from '#shared/utils/urls/public'

const props = defineProps<{ endpoint: ApiEndpointDetail | null; method?: ApiMethod | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const state = reactive({ method: 'POST' as ApiMethod, record: '', body: '', key: '', keepKey: false, headers: {} as Record<string, string> })
const result = ref<ApiTryResult | null>(null)
const history = ref<{ method: ApiMethod; status: number; ms: number; at: number }[]>([])
const bodyError = ref<string>()
const tab = ref<'body' | 'headers'>('body')
const answerTab = ref<'body' | 'headers'>('body')
const newKey = () => crypto.randomUUID()
watch([open, () => props.endpoint?.id], ([value]) => {
  if (!value || !props.endpoint) return
  result.value = null
  history.value = []
  bodyError.value = undefined
  state.method = props.method && props.endpoint.methods.includes(props.method) ? props.method : (props.endpoint.methods[0] ?? 'GET')
  state.record = ''
  state.body = JSON.stringify(exampleRequestBody(props.endpoint.fields), null, 2)
  state.key = newKey()
  state.keepKey = false
  state.headers = Object.fromEntries(props.endpoint.headers.map(header => [header.name, header.value ?? '']))
  tab.value = state.method === 'POST' || state.method === 'PUT' ? 'body' : 'headers'
}, { immediate: true })
const writes = computed(() => state.method === 'POST' || state.method === 'PUT')
const needsRecord = computed(() => state.method === 'PUT' || state.method === 'DELETE')
const canRecord = computed(() => needsRecord.value || state.method === 'GET')
watch(() => state.method, () => (tab.value = writes.value ? 'body' : 'headers'))

const sending = ref(false)
async function send() {
  if (!props.endpoint || sending.value) return
  let body: unknown
  if (writes.value) {
    try {
      body = JSON.parse(state.body || '{}')
      bodyError.value = undefined
    } catch {
      bodyError.value = t('apiService.docs.console.badJson')
      tab.value = 'body'
      return
    }
  }
  sending.value = true
  try {
    const headers: Record<string, string> = Object.fromEntries(Object.entries(state.headers).filter(([, value]) => value))
    if (state.method === 'POST') headers['Formalie-Key'] = state.key
    result.value = (await api.post<ApiTryResult>(`/api-endpoints/${props.endpoint.id}/try`, { method: state.method, record_id: state.record.trim() || null, body, headers })).data
    history.value = [{ method: state.method, status: result.value.status, ms: result.value.duration_ms, at: Date.now() }, ...history.value].slice(0, 5)
    answerTab.value = 'body'
    if (state.method === 'POST' && !state.keepKey) state.key = newKey()
  } catch (error) {
    handle(error)
  } finally {
    sending.value = false
  }
}
defineShortcuts({ meta_enter: { usingInput: true, handler: () => open.value && void send() } })
const statusTone = (status: number) => (status >= 500 ? 'error' : status >= 400 ? 'warning' : 'success')
const bodyText = computed(() => (result.value ? JSON.stringify(result.value.body, null, 2) : ''))
const size = computed(() => new Blob([bodyText.value]).size)
const lines = computed(() => Math.max(state.body.split('\n').length, 12))
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="t('apiService.docs.console.title', { name: endpoint?.name ?? '' })"
    :description="t('apiService.docs.console.desc')"
    :ui="{ content: 'w-full sm:max-w-5xl', body: 'p-0 sm:p-0', header: 'border-b border-default' }"
  >
    <template #body>
      <div v-if="endpoint" class="grid min-h-full lg:grid-cols-2">
        <!-- The request -->
        <form class="flex min-w-0 flex-col gap-4 p-4 sm:p-5" @submit.prevent="send">
          <div class="flex flex-wrap gap-1.5" role="radiogroup" :aria-label="t('apiService.col.methods')">
            <button
              v-for="option in endpoint.methods"
              :key="option"
              type="button"
              role="radio"
              :aria-checked="state.method === option"
              class="rounded-md border px-2.5 py-1 font-mono text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
              :class="state.method === option ? ['border-current', METHOD_TEXT[option]] : 'border-default text-muted hover:text-highlighted'"
              @click="state.method = option"
            >
              {{ option }}
            </button>
          </div>

          <div class="flex min-w-0 items-stretch overflow-hidden rounded-lg border border-default bg-elevated/40 font-mono text-xs" dir="ltr">
            <span class="flex shrink-0 items-center px-3 font-semibold" :class="METHOD_TEXT[state.method]">{{ state.method }}</span>
            <span class="flex min-w-0 items-center truncate border-s border-default px-3 text-muted">/{{ endpoint.name }}</span>
            <template v-if="canRecord">
              <span class="flex items-center text-muted">/</span>
              <input v-model="state.record" class="min-w-0 flex-1 bg-transparent px-1 py-2 text-highlighted outline-none placeholder:text-dimmed" :placeholder="needsRecord ? t('apiService.docs.console.recordNeeded') : t('apiService.docs.console.recordPlaceholder')" :aria-label="t('apiService.docs.console.record')" >
            </template>
          </div>

          <UAlert v-if="endpoint.status !== 'active'" icon="i-lucide-flask-conical" color="neutral" variant="subtle" :description="t('apiService.docs.notLiveNote')" />

          <div class="flex gap-1 border-b border-default" role="tablist">
            <button v-for="item in (['body', 'headers'] as const)" :key="item" type="button" role="tab" :aria-selected="tab === item" class="-mb-px border-b-2 px-3 py-1.5 text-sm transition-colors" :class="tab === item ? 'border-(--ui-border-inverted) font-medium text-highlighted' : 'border-transparent text-muted hover:text-highlighted'" @click="tab = item">
              {{ item === 'body' ? t('apiService.docs.body') : t('apiService.docs.console.headers') }}
            </button>
          </div>

          <div v-if="tab === 'body'" class="flex flex-col gap-2">
            <p v-if="!writes" class="text-sm text-muted">{{ t('apiService.docs.console.noBody') }}</p>
            <template v-else>
              <div class="flex overflow-hidden rounded-lg bg-neutral-950" dir="ltr">
                <div class="shrink-0 py-3 ps-3 pe-2 text-end font-mono text-xs leading-relaxed text-neutral-600 select-none" aria-hidden="true">
                  <div v-for="n in lines" :key="n">{{ n }}</div>
                </div>
                <textarea v-model="state.body" spellcheck="false" wrap="off" :rows="lines" class="min-w-0 flex-1 resize-none overflow-x-auto bg-transparent py-3 pe-3 font-mono text-xs leading-relaxed text-neutral-100 outline-none" :aria-label="t('apiService.docs.body')" />
              </div>
              <p v-if="bodyError" class="text-sm text-error">{{ bodyError }}</p>
              <p class="text-xs text-muted">{{ t('apiService.docs.console.bodyHint') }}</p>
            </template>
          </div>

          <ul v-else class="flex flex-col divide-y divide-default rounded-lg border border-default text-sm">
            <li class="flex items-center gap-3 px-3 py-2">
              <code class="w-36 shrink-0 font-mono text-xs text-highlighted">Authorization</code>
              <span class="min-w-0 flex-1 truncate font-mono text-xs text-muted">Bearer {{ t('apiService.docs.console.testToken') }}</span>
              <UIcon name="i-lucide-lock" class="size-3.5 text-muted" />
            </li>
            <li v-if="writes" class="flex items-center gap-3 px-3 py-2">
              <code class="w-36 shrink-0 font-mono text-xs text-highlighted">Content-Type</code>
              <span class="min-w-0 flex-1 font-mono text-xs text-muted">application/json</span>
              <UIcon name="i-lucide-lock" class="size-3.5 text-muted" />
            </li>
            <li v-if="state.method === 'POST'" class="flex flex-col gap-2 px-3 py-2">
              <div class="flex items-center gap-3">
                <code class="w-36 shrink-0 font-mono text-xs text-highlighted">Formalie-Key</code>
                <input v-model="state.key" class="min-w-0 flex-1 bg-transparent font-mono text-xs text-highlighted outline-none" dir="ltr" :aria-label="'Formalie-Key'" >
                <UButton icon="i-lucide-refresh-cw" color="neutral" variant="ghost" size="xs" square :aria-label="t('apiService.docs.console.newKey')" @click="state.key = newKey()" />
              </div>
              <UCheckbox v-model="state.keepKey" :label="t('apiService.docs.console.keepKey')" :description="t('apiService.docs.console.keyHelp')" color="neutral" size="sm" />
            </li>
            <li v-for="(_, name) in state.headers" :key="name" class="flex items-center gap-3 px-3 py-2">
              <code class="w-36 shrink-0 truncate font-mono text-xs text-highlighted" dir="ltr">{{ name }}</code>
              <input v-model="state.headers[name]" class="min-w-0 flex-1 bg-transparent font-mono text-xs text-highlighted outline-none placeholder:text-dimmed" :placeholder="t('apiService.docs.console.headerHelp')" dir="ltr" >
            </li>
          </ul>

          <div class="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-default pt-4">
            <span class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-flask-conical" class="size-3.5" />{{ t('apiService.docs.console.testOnly') }}</span>
            <UButton type="submit" :label="t('apiService.docs.console.send')" icon="i-lucide-send" color="neutral" :loading="sending">
              <template #trailing><UKbd value="meta" size="sm" class="hidden sm:inline-flex" /><UKbd value="enter" size="sm" class="hidden sm:inline-flex" /></template>
            </UButton>
          </div>
        </form>

        <!-- The answer -->
        <div class="flex min-w-0 flex-col gap-3 border-t border-default bg-neutral-950 p-4 text-neutral-100 sm:p-5 lg:border-s lg:border-t-0">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <span class="text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">{{ t('apiService.call.answer') }}</span>
            <div v-if="result" class="flex items-center gap-2 font-mono text-xs" :class="sending ? 'opacity-60' : ''">
              <UBadge :label="String(result.status)" :color="statusTone(result.status)" variant="solid" size="sm" class="rounded-md font-mono" />
              <span class="text-neutral-400 tabular-nums">{{ t('dataSources.ms', { n: result.duration_ms }) }}</span>
              <span class="text-neutral-400 tabular-nums">{{ size }} B</span>
            </div>
          </div>
          <div v-if="!result && !sending" class="flex flex-1 flex-col items-center justify-center gap-2 py-16 text-center text-neutral-400">
            <UIcon name="i-lucide-send" class="size-8" />
            <span class="text-sm">{{ t('apiService.docs.console.nothingYet') }}</span>
          </div>
          <USkeleton v-else-if="sending && !result" class="h-64 w-full bg-neutral-800" />
          <template v-if="result">
            <div class="flex gap-1">
              <button v-for="item in (['body', 'headers'] as const)" :key="item" type="button" class="rounded-md px-2 py-0.5 text-xs transition-colors" :class="answerTab === item ? 'bg-neutral-800 text-white' : 'text-neutral-400 hover:text-neutral-200'" @click="answerTab = item">
                {{ item === 'body' ? t('apiService.docs.body') : t('apiService.docs.console.headers') }}
              </button>
            </div>
            <pre v-if="answerTab === 'body'" class="max-h-[60dvh] overflow-auto rounded-lg bg-neutral-900 p-3 font-mono text-xs leading-relaxed text-neutral-100" dir="ltr">{{ bodyText }}</pre>
            <ul v-else class="flex flex-col gap-1 rounded-lg bg-neutral-900 p-3 font-mono text-xs" dir="ltr">
              <li v-for="(value, name) in result.headers" :key="name"><span class="text-neutral-400">{{ name }}:</span> {{ value }}</li>
            </ul>
          </template>
          <div v-if="history.length > 1" class="mt-auto flex flex-col gap-1 border-t border-neutral-800 pt-3">
            <span class="text-[11px] font-semibold tracking-wide text-neutral-400 uppercase">{{ t('apiService.docs.console.recent') }}</span>
            <div v-for="item in history" :key="item.at" class="flex items-center gap-2 font-mono text-[11px] text-neutral-300">
              <span class="w-12" :class="METHOD_TEXT[item.method]">{{ item.method }}</span>
              <span class="size-1.5 rounded-full" :class="item.status < 300 ? 'bg-green-400' : item.status < 500 ? 'bg-amber-400' : 'bg-red-400'" />
              <span class="tabular-nums">{{ item.status }}</span>
              <span class="text-neutral-500 tabular-nums">{{ t('dataSources.ms', { n: item.ms }) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </USlideover>
</template>

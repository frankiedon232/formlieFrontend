<!--
  Try it (F13 M5): one call to an endpoint through every real check, with a test token made for the
  console (nothing is ever stored). The body starts from the example with the form's real answer
  values; a fresh Formalie-Key is filled in for every new POST (keep it to see a retry answered with
  the first record). The answer shows its status, time taken, headers and JSON.
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
const bodyError = ref<string>()
const newKey = () => crypto.randomUUID()
watch(open, value => {
  if (!value || !props.endpoint) return
  result.value = null
  bodyError.value = undefined
  state.method = props.method && props.endpoint.methods.includes(props.method) ? props.method : (props.endpoint.methods[0] ?? 'GET')
  state.record = ''
  state.body = JSON.stringify(exampleRequestBody(props.endpoint.fields), null, 2)
  state.key = newKey()
  state.keepKey = false
  state.headers = Object.fromEntries(props.endpoint.headers.map(header => [header.name, '']))
})
const methods = computed(() => (props.endpoint?.methods ?? []).map(method => ({ value: method, label: method })))
const writes = computed(() => state.method === 'POST' || state.method === 'PUT')
const needsRecord = computed(() => state.method === 'PUT' || state.method === 'DELETE')

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
      return
    }
  }
  sending.value = true
  try {
    const headers: Record<string, string> = Object.fromEntries(Object.entries(state.headers).filter(([, value]) => value))
    if (state.method === 'POST') headers['Formalie-Key'] = state.key
    result.value = (await api.post<ApiTryResult>(`/api-endpoints/${props.endpoint.id}/try`, { method: state.method, record_id: state.record.trim() || null, body, headers })).data
    if (state.method === 'POST' && !state.keepKey) state.key = newKey()
  } catch (error) {
    handle(error)
  } finally {
    sending.value = false
  }
}
const statusColor = computed(() => (!result.value ? 'neutral' : result.value.status >= 500 ? 'error' : result.value.status >= 400 ? 'warning' : 'success'))
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('apiService.docs.console.title', { name: endpoint?.name ?? '' })" :description="t('apiService.docs.console.desc')" :ui="{ content: 'sm:max-w-3xl' }">
    <template #body>
      <div class="grid gap-5 lg:grid-cols-2">
        <form id="api-try" class="flex min-w-0 flex-col gap-4" @submit.prevent="send">
          <div class="flex flex-wrap items-end gap-3">
            <UFormField :label="t('apiService.col.methods')">
              <UTabs v-model="state.method" :items="methods" :content="false" color="neutral" size="sm" :ui="{ ...SEGMENTED_UI, label: 'font-mono' }" />
            </UFormField>
            <UFormField v-if="needsRecord || state.method === 'GET'" :label="t('apiService.docs.console.record')" :hint="state.method === 'GET' ? t('apiService.optional') : undefined" class="min-w-0 flex-1">
              <UInput v-model="state.record" :placeholder="t('apiService.docs.console.recordPlaceholder')" class="w-full" :ui="{ base: 'font-mono' }" dir="ltr" />
            </UFormField>
          </div>
          <UFormField v-if="writes" :label="t('apiService.docs.body')" :error="bodyError">
            <UTextarea v-model="state.body" :rows="12" autoresize :maxrows="18" class="w-full" :ui="{ base: 'font-mono text-xs' }" dir="ltr" spellcheck="false" />
          </UFormField>
          <UFormField v-if="state.method === 'POST'" label="Formalie-Key" :help="t('apiService.docs.console.keyHelp')">
            <div class="flex flex-col gap-2">
              <UFieldGroup class="w-full">
                <UInput v-model="state.key" class="min-w-0 flex-1" :ui="{ base: 'font-mono text-xs' }" dir="ltr" />
                <UButton icon="i-lucide-refresh-cw" color="neutral" variant="outline" :aria-label="t('apiService.docs.console.newKey')" @click="state.key = newKey()" />
              </UFieldGroup>
              <UCheckbox v-model="state.keepKey" :label="t('apiService.docs.console.keepKey')" color="neutral" />
            </div>
          </UFormField>
          <UFormField v-for="(_, name) in state.headers" :key="name" :label="String(name)" :help="t('apiService.docs.console.headerHelp')">
            <UInput v-model="state.headers[name]" class="w-full" :ui="{ base: 'font-mono text-xs' }" dir="ltr" />
          </UFormField>
          <UAlert icon="i-lucide-flask-conical" color="neutral" variant="subtle" :description="t('apiService.docs.console.testOnly')" />
        </form>

        <div class="flex min-w-0 flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('apiService.call.answer') }}</h3>
          <AppEmpty v-if="!result && !sending" size="xs" icon="i-lucide-send" :title="t('apiService.docs.console.nothingYet')" />
          <USkeleton v-else-if="sending && !result" class="h-48 w-full" />
          <template v-if="result">
            <div class="flex flex-wrap items-center gap-2" :class="sending ? 'opacity-60' : ''">
              <UBadge :label="String(result.status)" :color="statusColor" variant="subtle" class="rounded-md font-mono" />
              <span class="text-xs text-muted tabular-nums">{{ t('dataSources.ms', { n: result.duration_ms }) }}</span>
              <span v-for="(value, name) in result.headers" :key="name" class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ name }}: {{ value }}</span>
            </div>
            <pre class="max-h-[26rem] overflow-auto rounded-lg border border-default bg-elevated/50 p-3 font-mono text-xs leading-relaxed text-default" dir="ltr">{{ JSON.stringify(result.body, null, 2) }}</pre>
          </template>
        </div>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.close')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" form="api-try" :label="t('apiService.docs.console.send')" icon="i-lucide-send" color="neutral" :loading="sending" />
      </div>
    </template>
  </AppModal>
</template>

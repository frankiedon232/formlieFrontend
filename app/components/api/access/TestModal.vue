<!--
  Test a caller against the access rules (F13 M3): pick an endpoint and say who calls (IP address,
  the website it comes from for browser callers, the country), and see whether it gets in, and why:
  the rule that decided, or "no allow rule matched".
-->
<script setup lang="ts">
import { API_NETWORKS, type ApiAccessTestRequest, type ApiAccessTestResult, type ApiEndpoint, type ApiNetwork } from '#shared/types/apiService'
import { checkRuleValue } from '#shared/utils/apiService/access'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ rule: [id: string] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const countryOptions = useCountryOptions()
const format = useRuleFormat()

const state = reactive({ endpoint: '', ip: '', origin: '', country: '', networks: [] as ApiNetwork[] })
const networkItems = computed(() => API_NETWORKS.map(value => ({ value, label: t(`apiService.access.network.${value}`) })))
const endpoints = ref<ApiEndpoint[]>([])
const result = ref<ApiAccessTestResult | null>(null)
watch(open, async value => {
  if (!value) return
  result.value = null
  try {
    endpoints.value = (await api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' }, { background: true })).data
    if (!state.endpoint && endpoints.value[0]) state.endpoint = endpoints.value[0].id
  } catch {
    endpoints.value = []
  }
})
watch(() => ({ ...state }), () => (result.value = null), { deep: true })
const endpointItems = computed(() => endpoints.value.map(item => ({ value: item.id, label: `/${item.name}` })))
const ipError = computed(() => (state.ip && (checkRuleValue('ip', state.ip) || state.ip.includes('/')) ? t('apiService.access.invalid.ip', { value: state.ip }) : undefined))
const busy = ref(false)
async function check() {
  if (!state.endpoint || !state.ip || ipError.value || busy.value) return
  busy.value = true
  try {
    const body: ApiAccessTestRequest = { endpoint_id: state.endpoint, ip: state.ip.trim(), origin: state.origin.trim() || null, country: state.country || null, networks: state.networks }
    result.value = (await api.post<ApiAccessTestResult>('/api-access-rules/test', body)).data
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="t('apiService.access.test.title')" :description="t('apiService.access.test.desc')" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <form id="api-rule-test" class="flex flex-col gap-4" @submit.prevent="check">
        <UFormField :label="t('apiService.col.endpoint')" required>
          <USelectMenu v-model="state.endpoint" :items="endpointItems" value-key="value" class="w-full" :ui="{ itemLabel: 'font-mono' }" />
        </UFormField>
        <UFormField :label="t('apiService.access.test.ip')" :error="ipError" required>
          <UInput v-model="state.ip" placeholder="203.0.113.10" class="w-full" :ui="{ base: 'font-mono' }" dir="ltr" />
        </UFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('apiService.access.test.origin')" :hint="t('apiService.optional')">
            <UInput v-model="state.origin" placeholder="https://www.example.com" class="w-full" :ui="{ base: 'font-mono' }" dir="ltr" />
          </UFormField>
          <UFormField :label="t('apiService.access.kind.country')" :hint="t('apiService.optional')">
            <USelectMenu v-model="state.country" :items="countryOptions" value-key="value" class="w-full" :placeholder="t('apiService.access.test.anyCountry')" />
          </UFormField>
          <UFormField :label="t('apiService.access.kind.network')" :hint="t('apiService.optional')" class="sm:col-span-2">
            <UCheckboxGroup v-model="state.networks" :items="networkItems" orientation="horizontal" color="neutral" />
          </UFormField>
        </div>
      </form>
      <div v-if="result" class="mt-5 flex flex-col gap-2 rounded-lg border p-4" :class="result.allowed ? 'border-success/40 bg-success/5' : 'border-error/40 bg-error/5'" role="status">
        <div class="flex items-center gap-2">
          <UIcon :name="result.allowed ? 'i-lucide-circle-check' : 'i-lucide-ban'" class="size-5" :class="result.allowed ? 'text-success' : 'text-error'" />
          <span class="text-base font-semibold text-highlighted">{{ result.allowed ? t('apiService.access.test.allowed') : t('apiService.access.test.refused') }}</span>
        </div>
        <p class="text-sm text-muted">
          <template v-if="result.rule">{{ t(`apiService.access.test.because.${result.rule.action}`, { value: format.valueText(result.rule.kind, result.rule.value), scope: format.scopeText(result.rule.scope) }) }}</template>
          <template v-else-if="result.reason === 'not_allowed'">{{ t('apiService.access.test.noAllow') }}</template>
          <template v-else>{{ t('apiService.access.test.noRules', { n: result.checked }, result.checked) }}</template>
        </p>
        <p v-if="result.region" class="text-xs text-muted">{{ t('apiService.access.test.region', { region: t(`apiService.access.region.${result.region}`) }) }}</p>
        <UButton v-if="result.rule" :label="t('apiService.access.test.openRule')" trailing-icon="i-lucide-arrow-up-right" color="neutral" variant="outline" size="xs" class="w-fit" @click="emit('rule', result.rule.id)" />
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.close')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" form="api-rule-test" :label="t('apiService.access.test.check')" icon="i-lucide-shield-question" color="neutral" :loading="busy" :disabled="!state.endpoint || !state.ip" />
      </div>
    </template>
  </AppModal>
</template>

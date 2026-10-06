<!--
  New / edit access rule (F13 M3): Allow or Block; what it matches (IP addresses or ranges, website
  domains, countries or regions); where it applies (the whole API, a service or one endpoint); a note;
  on / off. IPs and domains one per line, checked as you type; countries and regions picked from lists.
-->
<script setup lang="ts">
import type { ApiAccessRule, ApiAccessRuleSaveRequest, ApiEndpoint, ApiRuleKind, ApiService } from '#shared/types/apiService'
import { checkRuleValue, REGIONS } from '#shared/utils/apiService/access'

const props = defineProps<{ rule?: ApiAccessRule | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [rule: ApiAccessRule] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const countryOptions = useCountryOptions()
const format = useRuleFormat()

const state = reactive({ action: 'block' as 'allow' | 'block', kind: 'ip' as ApiRuleKind, text: '', picked: [] as string[], scope: 'all' as 'all' | 'service' | 'endpoint', target: '' as string, note: '', enabled: true })
const services = ref<ApiService[]>([])
const endpoints = ref<ApiEndpoint[]>([])
const shown = ref(false)
watch(open, async value => {
  if (!value) return
  shown.value = false
  const rule = props.rule
  Object.assign(state, {
    action: rule?.action ?? 'block',
    kind: rule?.kind ?? 'ip',
    text: rule && (rule.kind === 'ip' || rule.kind === 'domain') ? rule.values.join('\n') : '',
    picked: rule && (rule.kind === 'country' || rule.kind === 'region') ? [...rule.values] : [],
    scope: rule?.scope.type ?? 'all',
    target: rule?.scope.id ?? '',
    note: rule?.note ?? '',
    enabled: rule?.enabled ?? true,
  })
  try {
    const [a, b] = await Promise.all([api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' }, { background: true }), api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' }, { background: true })])
    services.value = a.data
    endpoints.value = b.data
  } catch {
    services.value = []
  }
})
watch(() => state.kind, (kind, old) => {
  if (!old || kind === old) return
  state.text = ''
  state.picked = []
})
const typed = computed(() => state.kind === 'ip' || state.kind === 'domain')
const values = computed(() => (typed.value ? state.text.split(/[\n,]+/).map(value => value.trim()).filter(Boolean) : state.picked))
const problems = computed(() => values.value.map(value => ({ value, problem: checkRuleValue(state.kind, value) })).filter(item => item.problem))
const actions = computed(() => [
  { value: 'block', label: t('apiService.access.action.block') },
  { value: 'allow', label: t('apiService.access.action.allow') },
])
const kinds = computed(() => (['ip', 'domain', 'country', 'region'] as const).map(kind => ({ value: kind, label: format.kindLabel(kind), description: t(`apiService.access.kindHint.${kind}`) })))
const regionItems = computed(() => Object.keys(REGIONS).map(code => ({ value: code, label: t(`apiService.access.region.${code}`) })))
const scopes = computed(() => [
  { value: 'all', label: t('apiService.access.scope.all') },
  { value: 'service', label: t('apiService.access.scope.service') },
  { value: 'endpoint', label: t('apiService.access.scope.endpoint') },
])
const targetItems = computed(() => (state.scope === 'service' ? services.value.map(item => ({ value: item.id, label: item.name })) : endpoints.value.map(item => ({ value: item.id, label: `/${item.name}` }))))
watch(() => state.scope, () => (state.target = ''))
const errors = computed(() => ({
  values: !values.value.length ? t('apiService.access.invalid.required') : problems.value.length ? t(`apiService.access.invalid.${problems.value[0]!.problem}`, { value: problems.value[0]!.value }) : undefined,
  target: state.scope !== 'all' && !state.target ? t('apiService.invalid.required') : undefined,
}))

const saving = ref(false)
async function save() {
  shown.value = true
  if (errors.value.values || errors.value.target || saving.value) return
  saving.value = true
  try {
    const body: ApiAccessRuleSaveRequest = { action: state.action, kind: state.kind, values: values.value, scope: { type: state.scope, id: state.scope === 'all' ? null : state.target }, note: state.note.trim() || null, enabled: state.enabled }
    const { data } = props.rule ? await api.patch<ApiAccessRule>(`/api-access-rules/${props.rule.id}`, body) : await api.post<ApiAccessRule>('/api-access-rules', body)
    emit('saved', data)
    open.value = false
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="rule ? t('apiService.access.editTitle') : t('apiService.access.newTitle')" :description="t('apiService.access.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <form id="api-rule-form" class="flex flex-col gap-5" @submit.prevent="save">
        <UFormField :label="t('apiService.access.col.action')" :help="t(`apiService.access.actionHint.${state.action}`)">
          <UTabs v-model="state.action" :items="actions" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" />
        </UFormField>
        <UFormField :label="t('apiService.access.col.kind')">
          <URadioGroup v-model="state.kind" :items="kinds" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
        </UFormField>
        <UFormField :label="t(`apiService.access.valuesLabel.${state.kind}`)" :error="shown ? errors.values : undefined" :help="t(`apiService.access.valuesHelp.${state.kind}`)" required>
          <UTextarea v-if="typed" v-model="state.text" :rows="4" autoresize class="w-full" :ui="{ base: 'font-mono text-sm' }" dir="ltr" :placeholder="state.kind === 'ip' ? '203.0.113.10\n198.51.100.0/24' : 'example.com\n*.example.com'" />
          <USelectMenu v-else-if="state.kind === 'country'" v-model="state.picked" :items="countryOptions" value-key="value" multiple :search-input="{ placeholder: t('apiService.access.searchCountries') }" :placeholder="t('apiService.access.pickCountries')" class="w-full" />
          <UCheckboxGroup v-else v-model="state.picked" :items="regionItems" color="neutral" variant="card" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2' }" />
        </UFormField>
        <UFormField :label="t('apiService.access.col.scope')" :error="shown ? errors.target : undefined">
          <div class="flex flex-col gap-2 sm:flex-row">
            <USelect v-model="state.scope" :items="scopes" class="w-full sm:w-48" />
            <USelectMenu v-if="state.scope !== 'all'" v-model="state.target" :items="targetItems" value-key="value" :placeholder="t('apiService.access.pickTarget')" class="min-w-0 flex-1" />
          </div>
        </UFormField>
        <UAlert v-if="state.action === 'allow' && state.kind === 'domain'" icon="i-lucide-info" color="neutral" variant="subtle" :description="t('apiService.access.domainAllowNote')" />
        <UFormField :label="t('apiService.access.col.note')" :hint="t('apiService.optional')">
          <UInput v-model="state.note" maxlength="300" class="w-full" :placeholder="t('apiService.access.notePlaceholder')" />
        </UFormField>
        <USwitch v-model="state.enabled" :label="t('apiService.access.enabled')" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" form="api-rule-form" :label="rule ? t('common.save') : t('apiService.access.create')" color="neutral" :loading="saving" />
      </div>
    </template>
  </AppModal>
</template>

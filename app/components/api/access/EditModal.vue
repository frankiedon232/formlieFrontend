<!--
  New / edit access rule (F13 M3; guided in steps since M7, owner 2026-10-06). New: 1 What access
  rules do, Allow or Block, what it matches (IP addresses or ranges, website domains, countries,
  regions, anonymous networks) → 2 The values (IPs and domains as chips: comma, space or Enter
  adds one, each checked; countries, regions and networks picked from lists) → 3 Where it applies,
  a note, on / off → 4 Saved, and what comes next. Editing shows the steps' fields on one page.
-->
<script setup lang="ts">
import { API_NETWORKS, type ApiAccessRule, type ApiAccessRuleSaveRequest, type ApiEndpoint, type ApiRuleKind, type ApiService } from '#shared/types/apiService'
import { checkRuleValue, normaliseRuleValue, REGIONS } from '#shared/utils/apiService/access'

const props = defineProps<{ rule?: ApiAccessRule | null; presetEndpoint?: string | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [rule: ApiAccessRule]; test: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const countryOptions = useCountryOptions()
const format = useRuleFormat()
const setup = useApiSetup()

const state = reactive({ action: 'block' as 'allow' | 'block', kind: 'ip' as ApiRuleKind, tags: [] as string[], picked: [] as string[], scope: 'all' as 'all' | 'service' | 'endpoint', target: '' as string, note: '', enabled: true })
const services = ref<ApiService[]>([])
const endpoints = ref<ApiEndpoint[]>([])
const shown = ref(false)
const step = ref(0)
const saved = ref<ApiAccessRule | null>(null)
const tagError = ref<string>()
const typed = (kind: ApiRuleKind) => kind === 'ip' || kind === 'domain'
watch(open, async value => {
  if (!value) return
  shown.value = false
  step.value = 0
  saved.value = null
  tagError.value = undefined
  const rule = props.rule
  Object.assign(state, {
    action: rule?.action ?? 'block',
    kind: rule?.kind ?? 'ip',
    tags: rule && typed(rule.kind) ? [...rule.values] : [],
    picked: rule && !typed(rule.kind) ? [...rule.values] : [],
    scope: rule?.scope.type ?? (props.presetEndpoint ? 'endpoint' : 'all'),
    target: rule?.scope.id ?? props.presetEndpoint ?? '',
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
}, { immediate: true })
watch(() => state.kind, (kind, old) => {
  if (!old || kind === old) return
  state.tags = []
  state.picked = []
  tagError.value = undefined
})
// Chips: each value is checked as it is added; a wrong one stays in the box with the reason
const chips = useTemplateRef<{ commit: () => boolean }>('chips')
const checkTag = (value: string) => (checkRuleValue(state.kind, value) ? t(`apiService.access.invalid.${state.kind}`, { value }) : null)
const tidyTag = (value: string) => normaliseRuleValue(state.kind, value)

const values = computed(() => (typed(state.kind) ? state.tags : state.picked))
const steps = computed(() => [
  { title: t('apiService.access.steps.what'), icon: 'i-lucide-shield' },
  { title: t('apiService.access.steps.values'), icon: 'i-lucide-list' },
  { title: t('apiService.access.steps.where'), icon: 'i-lucide-target' },
  { title: t('apiService.access.steps.done'), icon: 'i-lucide-check' },
].map((item, i) => ({ ...item, value: i + 1 })))
const actions = computed(() => (['block', 'allow'] as const).map(value => ({ value, label: t(`apiService.access.action.${value}`), description: t(`apiService.access.actionHint.${value}`) })))
const kinds = computed(() => (['ip', 'domain', 'country', 'region', 'network'] as const).map(kind => ({ value: kind, label: format.kindLabel(kind), description: t(`apiService.access.kindHint.${kind}`) })))
const regionItems = computed(() => Object.keys(REGIONS).map(code => ({ value: code, label: t(`apiService.access.region.${code}`) })))
const networkItems = computed(() => API_NETWORKS.map(code => ({ value: code as string, label: t(`apiService.access.network.${code}`), description: t(`apiService.access.networkHint.${code}`) })))
const scopes = computed(() => [
  { value: 'all', label: t('apiService.access.scope.all') },
  { value: 'service', label: t('apiService.access.scope.service') },
  { value: 'endpoint', label: t('apiService.access.scope.endpoint') },
])
const targetItems = computed(() => (state.scope === 'service' ? services.value.map(item => ({ value: item.id, label: item.name })) : endpoints.value.map(item => ({ value: item.id, label: `/${item.name}` }))))
watch(() => state.scope, (scope, old) => old && (state.target = ''))
const errors = computed(() => ({
  values: !values.value.length ? t('apiService.access.invalid.required') : undefined,
  target: state.scope !== 'all' && !state.target ? t('apiService.invalid.required') : undefined,
}))

function toStep(target: number) {
  chips.value?.commit()
  if (target >= 2 && errors.value.values) {
    shown.value = true
    step.value = 1
    return
  }
  shown.value = false
  step.value = target
}
const saving = ref(false)
async function save() {
  chips.value?.commit()
  shown.value = true
  if (errors.value.values || errors.value.target || saving.value) {
    if (!props.rule && errors.value.values) step.value = 1
    return
  }
  saving.value = true
  try {
    const body: ApiAccessRuleSaveRequest = { action: state.action, kind: state.kind, values: values.value, scope: { type: state.scope, id: state.scope === 'all' ? null : state.target }, note: state.note.trim() || null, enabled: state.enabled }
    const { data } = props.rule ? await api.patch<ApiAccessRule>(`/api-access-rules/${props.rule.id}`, body) : await api.post<ApiAccessRule>('/api-access-rules', body)
    emit('saved', data)
    void setup.refresh()
    if (props.rule) open.value = false
    else {
      saved.value = data
      step.value = 3
    }
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
const showsStep = (n: number) => !!props.rule || step.value === n
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="rule ? t('apiService.access.editTitle') : t('apiService.access.newTitle')" :description="rule ? t('apiService.access.desc') : undefined" :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <div class="flex flex-col gap-5">
        <UStepper v-if="!rule" :model-value="step + 1" :items="steps" disabled color="neutral" size="xs" class="w-full" />

        <!-- 4 · Saved, what comes next -->
        <div v-if="saved" class="flex flex-col gap-4">
          <div class="flex items-start gap-3 rounded-lg border border-default p-4">
            <span class="flex size-10 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-check" class="size-5" /></span>
            <div class="flex min-w-0 flex-col gap-1">
              <span class="font-semibold text-highlighted">{{ t('apiService.access.done.title') }}</span>
              <span class="text-sm text-muted">{{ t(`apiService.access.done.${saved.action}`, { values: format.valuesText(saved), where: format.scopeText(saved.scope) }) }}</span>
            </div>
          </div>
          <div class="flex flex-col gap-2 rounded-lg bg-elevated/40 p-4">
            <span class="flex items-center gap-2 text-sm font-semibold text-highlighted"><UIcon name="i-lucide-flag" class="size-4" />{{ t('apiService.tokens.next.title') }}</span>
            <p class="text-sm text-muted">{{ t('apiService.access.done.next') }}</p>
            <ApiJourney :summary="setup.summary.value" focus="live" compact :actions="false" />
          </div>
        </div>

        <form v-else id="api-rule-form" class="flex flex-col gap-5" @submit.prevent="rule || step === 2 ? save() : toStep(step + 1)">
          <!-- 1 · What access rules do; allow or block; what it matches -->
          <template v-if="showsStep(0)">
            <div v-if="!rule" class="flex items-start gap-3 rounded-lg bg-elevated/40 p-4">
              <UIcon name="i-lucide-shield-check" class="mt-0.5 size-5 shrink-0 text-highlighted" />
              <div class="flex flex-col gap-1">
                <span class="text-sm font-semibold text-highlighted">{{ t('apiService.access.about.title') }}</span>
                <p class="text-sm text-muted">{{ t('apiService.access.about.text') }}</p>
              </div>
            </div>
            <UFormField :label="t('apiService.access.col.action')">
              <URadioGroup v-model="state.action" :items="actions" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
            </UFormField>
            <UFormField :label="t('apiService.access.col.kind')">
              <URadioGroup v-model="state.kind" :items="kinds" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
            </UFormField>
          </template>

          <!-- 2 · The values -->
          <template v-if="showsStep(1)">
            <UFormField :label="t(`apiService.access.valuesLabel.${state.kind}`)" :error="tagError ?? (shown ? errors.values : undefined)" :help="t(`apiService.access.valuesHelp.${state.kind}`)" required>
              <AppChipsInput v-if="typed(state.kind)" ref="chips" v-model="state.tags" :check="checkTag" :normalise="tidyTag" mono :placeholder="state.kind === 'ip' ? '203.0.113.10, 198.51.100.0/24' : 'example.com, *.example.com'" @error="message => (tagError = message ?? undefined)" />
              <USelectMenu v-else-if="state.kind === 'country'" v-model="state.picked" :items="countryOptions" value-key="value" multiple :search-input="{ placeholder: t('apiService.access.searchCountries') }" :placeholder="t('apiService.access.pickCountries')" class="w-full" />
              <UCheckboxGroup v-else-if="state.kind === 'region'" v-model="state.picked" :items="regionItems" color="neutral" variant="card" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2' }" />
              <UCheckboxGroup v-else v-model="state.picked" :items="networkItems" color="neutral" variant="card" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2' }" />
            </UFormField>
            <p v-if="typed(state.kind) && state.tags.length" class="text-xs text-muted">{{ t('apiService.access.valuesCount', { n: state.tags.length }, state.tags.length) }}</p>
            <UAlert v-if="state.kind === 'country' || state.kind === 'region'" icon="i-lucide-info" color="neutral" variant="subtle" :title="t('apiService.access.geo.title')" :description="t('apiService.access.geo.text')" />
            <UAlert v-if="state.kind === 'network'" icon="i-lucide-info" color="neutral" variant="subtle" :description="t('apiService.access.networkNote')" />
            <UAlert v-if="state.action === 'allow' && state.kind === 'domain'" icon="i-lucide-info" color="neutral" variant="subtle" :description="t('apiService.access.domainAllowNote')" />
          </template>

          <!-- 3 · Where, note, on / off -->
          <template v-if="showsStep(2)">
            <UFormField :label="t('apiService.access.col.scope')" :error="shown ? errors.target : undefined" :help="t('apiService.access.scopeHelp')">
              <div class="flex flex-col gap-2 sm:flex-row">
                <USelect v-model="state.scope" :items="scopes" class="w-full sm:w-48" />
                <USelectMenu v-if="state.scope !== 'all'" v-model="state.target" :items="targetItems" value-key="value" :placeholder="t('apiService.access.pickTarget')" class="min-w-0 flex-1" />
              </div>
            </UFormField>
            <UFormField :label="t('apiService.access.col.note')" :hint="t('apiService.optional')">
              <UInput v-model="state.note" maxlength="300" class="w-full" :placeholder="t('apiService.access.notePlaceholder')" />
            </UFormField>
            <USwitch v-model="state.enabled" :label="t('apiService.access.enabled')" />
          </template>
        </form>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-wrap justify-end gap-2">
        <template v-if="saved">
          <UButton :label="t('apiService.access.test.title')" icon="i-lucide-shield-question" color="neutral" variant="outline" @click="emit('test'); open = false" />
          <UButton :label="t('common.close')" color="neutral" @click="open = false" />
        </template>
        <template v-else-if="rule">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton type="submit" form="api-rule-form" :label="t('common.save')" color="neutral" :loading="saving" />
        </template>
        <template v-else>
          <UButton v-if="step > 0" :label="t('apiService.service.steps.back')" icon="i-lucide-arrow-left" color="neutral" variant="ghost" class="me-auto" @click="toStep(step - 1)" />
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton v-if="step < 2" type="submit" form="api-rule-form" :label="t('apiService.service.steps.continue')" trailing-icon="i-lucide-arrow-right" color="neutral" />
          <UButton v-else type="submit" form="api-rule-form" :label="t('apiService.access.create')" color="neutral" :loading="saving" />
        </template>
      </div>
    </template>
  </AppModal>
</template>

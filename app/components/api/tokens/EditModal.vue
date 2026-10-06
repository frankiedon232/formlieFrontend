<!--
  New token / edit token (F13 M2; guided in steps since M7, owner 2026-10-06). New: 1 What a token
  is, live or test, bearer or client id + secret → 2 Name and what it may call (services,
  endpoints, methods; empty = all; preset when opened from an endpoint) → 3 Expiry, short-lived
  lifetime, signed calls → 4 Its secrets (also viewable later in the panel, after the password)
  and what comes next. Editing: name, what it may call and the expiry on one page.
-->
<script setup lang="ts">
import type { ApiEndpoint, ApiService, ApiToken, ApiTokenCreated, ApiTokenSaveRequest } from '#shared/types/apiService'
import { TOKEN_EXPIRY_DAYS, TOKEN_LIFETIMES } from '#shared/utils/apiService/tokens'
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'

const props = defineProps<{ token?: ApiToken | null; base: string; presetEndpoint?: string | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [token: ApiToken] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const setup = useApiSetup()

const state = reactive({ name: '', mode: 'live' as 'live' | 'test', kind: 'static' as 'static' | 'client', services: [] as string[], endpoints: [] as string[], methods: [] as ApiMethod[], expiry: '365', custom: '', lifetime: 15, signing: false })
const services = ref<ApiService[]>([])
const endpoints = ref<ApiEndpoint[]>([])
const created = ref<ApiTokenCreated | null>(null)
const nameError = ref<string>()
const step = ref(0)
watch(open, async value => {
  if (!value) return
  created.value = null
  nameError.value = undefined
  step.value = 0
  const token = props.token
  Object.assign(state, {
    name: token?.name ?? '',
    mode: token?.mode ?? 'live',
    kind: token?.kind ?? 'static',
    services: [...(token?.scopes.services ?? [])],
    endpoints: [...(token?.scopes.endpoints ?? (props.presetEndpoint ? [props.presetEndpoint] : []))],
    methods: [...(token?.scopes.methods ?? [])],
    expiry: token ? (token.expires_at ? 'custom' : 'never') : '365',
    custom: token?.expires_at ? token.expires_at.slice(0, 10) : '',
    lifetime: token?.lifetime_minutes ?? 15,
    signing: token?.signing ?? false,
  })
  try {
    const [a, b] = await Promise.all([api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' }, { background: true }), api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' }, { background: true })])
    services.value = a.data
    endpoints.value = b.data
    const preset = props.presetEndpoint ? b.data.find(item => item.id === props.presetEndpoint) : undefined
    if (preset && !token && !state.name) state.name = t('apiService.tokens.presetName', { name: preset.name })
  } catch {
    services.value = []
  }
}, { immediate: true })
const steps = computed(() => [
  { title: t('apiService.tokens.steps.kind'), icon: 'i-lucide-key-round' },
  { title: t('apiService.tokens.steps.access'), icon: 'i-lucide-target' },
  { title: t('apiService.tokens.steps.safety'), icon: 'i-lucide-shield' },
  { title: t('apiService.tokens.steps.done'), icon: 'i-lucide-check' },
].map((item, i) => ({ ...item, value: i + 1 })))
const modes = computed(() => (['live', 'test'] as const).map(mode => ({ value: mode, label: t(`apiService.tokens.mode.${mode}`), description: t(`apiService.tokens.modeHint.${mode}`) })))
const kinds = computed(() => (['static', 'client'] as const).map(kind => ({ value: kind, label: t(`apiService.tokens.kind.${kind}`), description: t(`apiService.tokens.kindHint.${kind}`) })))
const serviceItems = computed(() => services.value.map(item => ({ label: item.name, value: item.id })))
const endpointItems = computed(() => endpoints.value.filter(item => !state.services.length || state.services.includes(item.service.id)).map(item => ({ label: `/${item.name}`, value: item.id })))
const expiryItems = computed(() => [...TOKEN_EXPIRY_DAYS.map(days => ({ value: days == null ? 'never' : String(days), label: days == null ? t('apiService.tokens.never') : t('apiService.tokens.inDays', { n: days }, days) })), { value: 'custom', label: t('apiService.tokens.customDate') }])
const lifetimeItems = TOKEN_LIFETIMES.map(n => ({ value: n, label: t('apiService.tokens.minutes', { n }) }))
const toggleMethod = (method: ApiMethod, on: boolean) => (state.methods = on ? API_METHODS.filter(item => item === method || state.methods.includes(item)) : state.methods.filter(item => item !== method))
watch(() => state.services, list => (state.endpoints = state.endpoints.filter(id => !list.length || endpoints.value.find(item => item.id === id && list.includes(item.service.id)))))
const scopeSummary = computed(() => {
  if (state.endpoints.length) return t('apiService.tokens.scopeSummary.endpoints', { n: state.endpoints.length }, state.endpoints.length)
  if (state.services.length) return t('apiService.tokens.scopeSummary.services', { n: state.services.length }, state.services.length)
  return t('apiService.tokens.scopeSummary.all')
})

function expiresAt(): string | null {
  if (state.expiry === 'never') return null
  if (state.expiry === 'custom') return state.custom ? new Date(`${state.custom}T23:59:59Z`).toISOString() : null
  return new Date(Date.now() + Number(state.expiry) * 86_400_000).toISOString()
}
function toStep(target: number) {
  if (target >= 2 && !state.name.trim()) {
    nameError.value = t('apiService.invalid.required')
    step.value = 1
    return
  }
  nameError.value = undefined
  step.value = target
}
const saving = ref(false)
async function save() {
  nameError.value = state.name.trim() ? undefined : t('apiService.invalid.required')
  if (nameError.value || saving.value) {
    if (nameError.value && !props.token) step.value = 1
    return
  }
  saving.value = true
  try {
    const scopes = { services: state.services, endpoints: state.endpoints, methods: state.methods }
    if (props.token) {
      const { data } = await api.patch<ApiToken>(`/api-tokens/${props.token.id}`, { name: state.name.trim(), scopes, expires_at: expiresAt(), ...(props.token.kind === 'client' ? { lifetime_minutes: state.lifetime } : {}) })
      emit('saved', data)
      open.value = false
    } else {
      const body: ApiTokenSaveRequest = { name: state.name.trim(), kind: state.kind, mode: state.mode, scopes, expires_at: expiresAt(), lifetime_minutes: state.kind === 'client' ? state.lifetime : null, signing: state.signing }
      const { data } = await api.post<ApiTokenCreated>('/api-tokens', body)
      created.value = data
      step.value = 3
      emit('saved', data.token)
      void setup.refresh()
    }
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
const nextRule = computed(() => ({ path: '/api-service/access', query: { new: '1', ...(props.presetEndpoint ? { endpoint: props.presetEndpoint } : {}) } }))
</script>

<template>
  <AppModal v-model:open="open" keep-open :dismissible="!created" :title="created ? t('apiService.tokens.createdTitle', { name: created.token.name }) : token ? t('apiService.tokens.editTitle') : t('apiService.tokens.newTitle')" :description="token ? t('apiService.tokens.desc') : undefined" :ui="{ content: 'sm:max-w-2xl' }">
    <template #body>
      <div class="flex flex-col gap-5">
        <UStepper v-if="!token" :model-value="step + 1" :items="steps" disabled color="neutral" size="xs" class="w-full" />

        <!-- 4 · Secrets and what comes next -->
        <template v-if="created">
          <ApiTokensSecrets :token="created.token" :secrets="created.secrets" :base="base" />
          <UAlert icon="i-lucide-eye" color="neutral" variant="subtle" :description="t('apiService.tokens.viewLater')" />
          <div class="flex flex-col gap-2 rounded-lg bg-elevated/40 p-4">
            <span class="flex items-center gap-2 text-sm font-semibold text-highlighted"><UIcon name="i-lucide-flag" class="size-4" />{{ t('apiService.tokens.next.title') }}</span>
            <p class="text-sm text-muted">{{ created.token.mode === 'test' ? t('apiService.tokens.next.test') : t('apiService.tokens.next.live') }}</p>
            <ApiJourney :summary="setup.summary.value" focus="access" compact :actions="false" />
          </div>
        </template>

        <form v-else id="api-token-form" class="flex flex-col gap-5" @submit.prevent="token || step === 2 ? save() : toStep(step + 1)">
          <!-- 1 · What a token is -->
          <template v-if="!token && step === 0">
            <div class="flex items-start gap-3 rounded-lg bg-elevated/40 p-4">
              <UIcon name="i-lucide-key-round" class="mt-0.5 size-5 shrink-0 text-highlighted" />
              <div class="flex flex-col gap-1">
                <span class="text-sm font-semibold text-highlighted">{{ t('apiService.tokens.about.title') }}</span>
                <p class="text-sm text-muted">{{ t('apiService.tokens.about.text') }}</p>
              </div>
            </div>
            <UFormField :label="t('apiService.tokens.col.mode')">
              <URadioGroup v-model="state.mode" :items="modes" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
            </UFormField>
            <UFormField :label="t('apiService.tokens.col.kind')">
              <URadioGroup v-model="state.kind" :items="kinds" variant="card" color="neutral" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
            </UFormField>
          </template>

          <!-- 2 · Name and what it may call -->
          <template v-if="token || step === 1">
            <UFormField :label="t('apiService.service.name')" :error="nameError" :help="t('apiService.tokens.nameHelp')" required>
              <UInput v-model="state.name" :placeholder="t('apiService.tokens.namePlaceholder')" class="w-full" maxlength="80" />
            </UFormField>
            <UFormField :label="t('apiService.tokens.scope.title')" :help="t('apiService.tokens.scope.help')">
              <div class="flex flex-col gap-2">
                <USelectMenu v-model="state.services" :items="serviceItems" value-key="value" multiple :placeholder="t('apiService.tokens.scope.allServices')" class="w-full" />
                <USelectMenu v-model="state.endpoints" :items="endpointItems" value-key="value" multiple :placeholder="t('apiService.tokens.scope.allEndpoints')" class="w-full" :ui="{ itemLabel: 'font-mono' }" />
                <div class="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1">
                  <span class="text-xs text-muted">{{ t('apiService.col.methods') }}</span>
                  <UCheckbox v-for="method in API_METHODS" :key="method" :model-value="state.methods.includes(method)" :label="method" color="neutral" :ui="{ label: 'font-mono text-xs' }" @update:model-value="value => toggleMethod(method, !!value)" />
                  <span v-if="!state.methods.length" class="text-xs text-muted">{{ t('apiService.tokens.scope.allMethods') }}</span>
                </div>
              </div>
            </UFormField>
            <p class="flex items-center gap-2 rounded-md border border-default px-3 py-2 text-xs text-muted"><UIcon name="i-lucide-target" class="size-4 shrink-0" />{{ scopeSummary }}</p>
          </template>

          <!-- 3 · Expiry, lifetime, signing -->
          <template v-if="token || step === 2">
            <div class="grid gap-4 sm:grid-cols-2">
              <UFormField :label="t('apiService.tokens.col.expires')" :help="token ? undefined : t('apiService.tokens.expiryHelp')">
                <USelect v-model="state.expiry" :items="expiryItems" class="w-full" />
                <UInput v-if="state.expiry === 'custom'" v-model="state.custom" type="date" class="mt-2 w-full" :min="new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)" />
              </UFormField>
              <UFormField v-if="state.kind === 'client'" :label="t('apiService.tokens.lifetime')" :help="t('apiService.tokens.lifetimeHelp')">
                <USelect v-model="state.lifetime" :items="lifetimeItems" class="w-full" />
              </UFormField>
            </div>
            <USwitch v-if="!token" v-model="state.signing" :label="t('apiService.tokens.signing')" :description="t('apiService.tokens.signingHelp')" />
          </template>
        </form>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-wrap justify-end gap-2">
        <template v-if="created">
          <UButton :label="t('apiService.tokens.next.rule')" icon="i-lucide-shield-plus" color="neutral" variant="outline" :to="nextRule" @click="open = false" />
          <UButton :label="t('apiService.tokens.copiedDone')" icon="i-lucide-check" color="neutral" @click="open = false" />
        </template>
        <template v-else-if="token">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton type="submit" form="api-token-form" :label="t('common.save')" color="neutral" :loading="saving" />
        </template>
        <template v-else>
          <UButton v-if="step > 0" :label="t('apiService.service.steps.back')" icon="i-lucide-arrow-left" color="neutral" variant="ghost" class="me-auto" @click="toStep(step - 1)" />
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton v-if="step < 2" type="submit" form="api-token-form" :label="t('apiService.service.steps.continue')" trailing-icon="i-lucide-arrow-right" color="neutral" />
          <UButton v-else type="submit" form="api-token-form" :label="t('apiService.tokens.create')" color="neutral" :loading="saving" />
        </template>
      </div>
    </template>
  </AppModal>
</template>

<!--
  New token / edit token (F13 M2). New: a name, live or test, a bearer token or client id + secret
  (short-lived tokens), what it may call (services, endpoints, methods; empty = all), when it
  expires and whether calls must be signed; then its secrets, shown once. Editing changes the name,
  what it may call and the expiry (kind, mode and signing stay; rotate for new secrets).
-->
<script setup lang="ts">
import type { ApiEndpoint, ApiService, ApiToken, ApiTokenCreated, ApiTokenSaveRequest, ApiTokenSecrets } from '#shared/types/apiService'
import { TOKEN_EXPIRY_DAYS, TOKEN_LIFETIMES } from '#shared/utils/apiService/tokens'
import { API_METHODS, type ApiMethod } from '#shared/utils/urls/public'

const props = defineProps<{ token?: ApiToken | null; base: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [token: ApiToken] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const state = reactive({ name: '', mode: 'live' as 'live' | 'test', kind: 'static' as 'static' | 'client', services: [] as string[], endpoints: [] as string[], methods: [] as ApiMethod[], expiry: '365', custom: '', lifetime: 15, signing: false })
const services = ref<ApiService[]>([])
const endpoints = ref<ApiEndpoint[]>([])
const created = ref<{ token: ApiToken; secrets: ApiTokenSecrets } | null>(null)
const nameError = ref<string>()
watch(open, async value => {
  if (!value) return
  created.value = null
  nameError.value = undefined
  const token = props.token
  Object.assign(state, {
    name: token?.name ?? '',
    mode: token?.mode ?? 'live',
    kind: token?.kind ?? 'static',
    services: [...(token?.scopes.services ?? [])],
    endpoints: [...(token?.scopes.endpoints ?? [])],
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
  } catch {
    services.value = []
  }
})
const modes = computed(() => [{ value: 'live', label: t('apiService.tokens.mode.live') }, { value: 'test', label: t('apiService.tokens.mode.test') }])
const kinds = computed(() => (['static', 'client'] as const).map(kind => ({ value: kind, label: t(`apiService.tokens.kind.${kind}`), description: t(`apiService.tokens.kindHint.${kind}`) })))
const serviceItems = computed(() => services.value.map(item => ({ label: item.name, value: item.id })))
const endpointItems = computed(() => endpoints.value.filter(item => !state.services.length || state.services.includes(item.service.id)).map(item => ({ label: `/${item.name}`, value: item.id })))
const expiryItems = computed(() => [...TOKEN_EXPIRY_DAYS.map(days => ({ value: days == null ? 'never' : String(days), label: days == null ? t('apiService.tokens.never') : t('apiService.tokens.inDays', { n: days }, days) })), { value: 'custom', label: t('apiService.tokens.customDate') }])
const lifetimeItems = TOKEN_LIFETIMES.map(n => ({ value: n, label: t('apiService.tokens.minutes', { n }) }))
const toggleMethod = (method: ApiMethod, on: boolean) => (state.methods = on ? API_METHODS.filter(item => item === method || state.methods.includes(item)) : state.methods.filter(item => item !== method))
watch(() => state.services, list => (state.endpoints = state.endpoints.filter(id => !list.length || endpoints.value.find(item => item.id === id && list.includes(item.service.id)))))

function expiresAt(): string | null {
  if (state.expiry === 'never') return null
  if (state.expiry === 'custom') return state.custom ? new Date(`${state.custom}T23:59:59Z`).toISOString() : null
  return new Date(Date.now() + Number(state.expiry) * 86_400_000).toISOString()
}
const saving = ref(false)
async function save() {
  nameError.value = state.name.trim() ? undefined : t('apiService.invalid.required')
  if (nameError.value || saving.value) return
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
      emit('saved', data.token)
    }
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :dismissible="!created" :title="created ? t('apiService.tokens.createdTitle', { name: created.token.name }) : token ? t('apiService.tokens.editTitle') : t('apiService.tokens.newTitle')" :description="created ? undefined : t('apiService.tokens.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <ApiTokensSecrets v-if="created" :token="created.token" :secrets="created.secrets" :base="base" />
      <form v-else id="api-token-form" class="flex flex-col gap-5" @submit.prevent="save">
        <UFormField :label="t('apiService.service.name')" :error="nameError" required>
          <UInput v-model="state.name" :placeholder="t('apiService.tokens.namePlaceholder')" class="w-full" autofocus maxlength="80" />
        </UFormField>
        <template v-if="!token">
          <UFormField :label="t('apiService.tokens.col.mode')" :help="t(`apiService.tokens.modeHint.${state.mode}`)">
            <UTabs v-model="state.mode" :items="modes" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" class="w-fit" />
          </UFormField>
          <UFormField :label="t('apiService.tokens.col.kind')">
            <URadioGroup v-model="state.kind" :items="kinds" variant="card" color="neutral" orientation="horizontal" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2', item: 'w-full' }" />
          </UFormField>
        </template>
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
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('apiService.tokens.col.expires')">
            <USelect v-model="state.expiry" :items="expiryItems" class="w-full" />
            <UInput v-if="state.expiry === 'custom'" v-model="state.custom" type="date" class="mt-2 w-full" :min="new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)" />
          </UFormField>
          <UFormField v-if="state.kind === 'client'" :label="t('apiService.tokens.lifetime')" :help="t('apiService.tokens.lifetimeHelp')">
            <USelect v-model="state.lifetime" :items="lifetimeItems" class="w-full" />
          </UFormField>
        </div>
        <USwitch v-if="!token" v-model="state.signing" :label="t('apiService.tokens.signing')" :description="t('apiService.tokens.signingHelp')" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton v-if="created" :label="t('apiService.tokens.copiedDone')" icon="i-lucide-check" color="neutral" @click="open = false" />
        <template v-else>
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton type="submit" form="api-token-form" :label="token ? t('common.save') : t('apiService.tokens.create')" color="neutral" :loading="saving" />
        </template>
      </div>
    </template>
  </AppModal>
</template>

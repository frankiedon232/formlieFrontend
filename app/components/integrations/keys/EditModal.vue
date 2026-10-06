<!--
  New / edit API key for Formalie's management API (F13 M6): a name, what it may do (scopes) and,
  when new, when it expires. The key itself is returned once (the page shows it). Editing changes
  the name and scopes only; a different expiry means a new key.
-->
<script setup lang="ts">
import { API_KEY_SCOPES, type ApiKeyScope, type ManagementKey, type ManagementKeySaveRequest, type ManagementKeyWithSecret } from '#shared/types/integrations'
import { TOKEN_EXPIRY_DAYS } from '#shared/utils/apiService/tokens'

const props = defineProps<{ apiKey?: ManagementKey | null }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [key: ManagementKey]; created: [result: ManagementKeyWithSecret] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const state = reactive({ name: '', scopes: [] as ApiKeyScope[], expiry: '365', custom: '' })
const shown = ref(false)
watch(open, value => {
  if (!value) return
  shown.value = false
  Object.assign(state, { name: props.apiKey?.name ?? '', scopes: props.apiKey ? [...props.apiKey.scopes] : ['forms:read', 'responses:read'], expiry: '365', custom: '' })
})
const scopeItems = computed(() => API_KEY_SCOPES.map(value => ({ value, label: t(`integrations.keys.scope.${value.replace(':', '_')}`), description: t(`integrations.keys.scopeHint.${value.replace(':', '_')}`) })))
const expiryItems = computed(() => [...TOKEN_EXPIRY_DAYS.map(days => ({ value: days == null ? 'never' : String(days), label: days == null ? t('apiService.tokens.never') : t('apiService.tokens.inDays', { n: days }, days) })), { value: 'custom', label: t('apiService.tokens.customDate') }])
function expiresAt(): string | null {
  if (state.expiry === 'never') return null
  if (state.expiry === 'custom') return state.custom ? new Date(`${state.custom}T23:59:59Z`).toISOString() : null
  return new Date(Date.now() + Number(state.expiry) * 86_400_000).toISOString()
}
const errors = computed(() => ({
  name: !state.name.trim() ? t('apiService.invalid.required') : undefined,
  scopes: !state.scopes.length ? t('integrations.keys.invalid.scopes') : undefined,
  custom: !props.apiKey && state.expiry === 'custom' && !state.custom ? t('apiService.invalid.required') : undefined,
}))

const saving = ref(false)
async function save() {
  shown.value = true
  if (Object.values(errors.value).some(Boolean) || saving.value) return
  saving.value = true
  try {
    if (props.apiKey) emit('saved', (await api.patch<ManagementKey>(`/api-keys/${props.apiKey.id}`, { name: state.name.trim(), scopes: state.scopes })).data)
    else {
      const body: ManagementKeySaveRequest = { name: state.name.trim(), scopes: state.scopes, expires_at: expiresAt() }
      emit('created', (await api.post<ManagementKeyWithSecret>('/api-keys', body)).data)
    }
    open.value = false
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppModal v-model:open="open" keep-open :title="apiKey ? t('integrations.keys.editTitle') : t('integrations.keys.newTitle')" :description="t('integrations.keys.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <form id="api-key-form" class="flex flex-col gap-5" @submit.prevent="save">
        <UFormField :label="t('integrations.keys.col.name')" :error="shown ? errors.name : undefined" required>
          <UInput v-model="state.name" maxlength="80" class="w-full" :placeholder="t('integrations.keys.namePlaceholder')" />
        </UFormField>
        <UFormField :label="t('integrations.keys.col.scopes')" :error="shown ? errors.scopes : undefined" :help="t('integrations.keys.scopesHelp')">
          <UCheckboxGroup v-model="state.scopes" :items="scopeItems" color="neutral" variant="card" :ui="{ fieldset: 'grid gap-2 sm:grid-cols-2' }" />
        </UFormField>
        <UFormField v-if="!apiKey" :label="t('apiService.tokens.col.expires')" :error="shown ? errors.custom : undefined">
          <USelect v-model="state.expiry" :items="expiryItems" class="w-full" />
          <UInput v-if="state.expiry === 'custom'" v-model="state.custom" type="date" class="mt-2 w-full" :min="new Date(Date.now() + 86_400_000).toISOString().slice(0, 10)" />
        </UFormField>
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton type="submit" form="api-key-form" :label="apiKey ? t('common.save') : t('integrations.keys.create')" color="neutral" :loading="saving" />
      </div>
    </template>
  </AppModal>
</template>

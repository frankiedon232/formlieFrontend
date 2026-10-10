<!--
  Rotate a token (F13 M2): new secrets, and how long the old ones keep working (stop at once, 24
  hours, 7 days) so callers can switch without downtime; then the new secrets, shown once.
  The same dialog rotates the organisation's address key (`target="key"`).
-->
<script setup lang="ts">
import type { ApiServiceSettings, ApiToken, ApiTokenCreated, ApiTokenSecrets } from '#shared/types/apiService'
import { ROTATION_GRACE_HOURS } from '#shared/utils/apiService/tokens'

const props = defineProps<{ token?: ApiToken | null; target: 'token' | 'key'; base: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ rotated: [token?: ApiToken]; key: [settings: ApiServiceSettings] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { dateTime } = useFormat()
// The key needs api.key, a token api.tokens (F22 R2 M4)
const { can } = useCan()
const allowed = computed(() => can(props.target === 'key' ? 'api.key' : 'api.tokens'))

const grace = ref(24)
const result = ref<{ token: ApiToken; secrets: ApiTokenSecrets } | null>(null)
const newKey = ref<ApiServiceSettings | null>(null)
watch(open, value => {
  if (!value) return
  grace.value = 24
  result.value = null
  newKey.value = null
})
const items = computed(() => ROTATION_GRACE_HOURS.map(hours => ({ value: hours, label: t(`apiService.rotate.grace.h${hours}`), description: t(`apiService.rotate.graceHint.h${hours}`) })))
const busy = ref(false)
async function rotate() {
  if (busy.value || !allowed.value) return
  busy.value = true
  try {
    if (props.target === 'key') {
      const { data } = await api.post<ApiServiceSettings>('/api-service/key/rotate', { grace_hours: grace.value })
      newKey.value = data
      emit('key', data)
    } else if (props.token) {
      const { data } = await api.post<ApiTokenCreated>(`/api-tokens/${props.token.id}/rotate`, { grace_hours: grace.value })
      result.value = data
      emit('rotated', data.token)
    }
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
const done = computed(() => !!result.value || !!newKey.value)
</script>

<template>
  <AppModal v-model:open="open" :dismissible="!result" :title="target === 'key' ? t('apiService.rotate.keyTitle') : t('apiService.rotate.title', { name: token?.name ?? '' })" :description="done ? undefined : target === 'key' ? t('apiService.rotate.keyDesc') : t('apiService.rotate.desc')" :ui="{ content: 'sm:max-w-xl' }">
    <template #body>
      <ApiTokensSecrets v-if="result" :token="result.token" :secrets="result.secrets" :base="base" />
      <div v-else-if="newKey" class="flex flex-col gap-3">
        <AppCopyField :value="newKey.api_key" :label="t('apiService.key.current')" monospace />
        <p class="text-sm text-muted">{{ newKey.previous_until ? t('apiService.rotate.keyGrace', { key: newKey.previous_key, until: dateTime(newKey.previous_until) }) : t('apiService.rotate.keyNow') }}</p>
      </div>
      <URadioGroup v-else v-model="grace" :items="items" variant="card" color="neutral" :legend="t('apiService.rotate.graceLegend')" :ui="{ fieldset: 'flex flex-col gap-2' }" />
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton v-if="done" :label="result ? t('apiService.tokens.copiedDone') : t('common.close')" icon="i-lucide-check" color="neutral" @click="open = false" />
        <template v-else>
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="t('apiService.rotate.confirm')" icon="i-lucide-refresh-cw" color="neutral" :loading="busy" :disabled="!allowed" @click="rotate" />
        </template>
      </div>
    </template>
  </AppModal>
</template>

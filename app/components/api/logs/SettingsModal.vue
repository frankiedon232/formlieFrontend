<!--
  Request log settings (F13 M4): keep request and response bodies or not (off by default; personal
  answers are always masked) and for how long. Tokens are never logged, only their visible part.
-->
<script setup lang="ts">
import type { ApiLogSettings } from '#shared/types/apiService'

const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ saved: [settings: ApiLogSettings] }>()
const { t } = useI18n()
const api = useApi()
const { busy, run } = useBusy()
const state = reactive<ApiLogSettings>({ keep_bodies: false, days: 7 })
watch(open, async value => {
  if (!value) return
  try {
    Object.assign(state, (await api.get<ApiLogSettings>('/api-logs/settings')).data)
  } catch {
    /* keeps the defaults shown */
  }
})
const days = computed(() => [1, 7, 30].map(n => ({ value: n, label: t('apiService.logs.settings.days', { n }, n) })))
const save = () =>
  run(
    async () => {
      const { data } = await api.put<ApiLogSettings>('/api-logs/settings', { ...state })
      emit('saved', data)
      open.value = false
    },
    { success: t('apiService.logs.settings.saved') },
  )
</script>

<template>
  <AppModal v-model:open="open" :title="t('apiService.logs.settings.title')" :description="t('apiService.logs.settings.desc')">
    <template #body>
      <div class="flex flex-col gap-4">
        <USwitch v-model="state.keep_bodies" :label="t('apiService.logs.settings.keep')" :description="t('apiService.logs.settings.keepHint')" />
        <UFormField v-if="state.keep_bodies" :label="t('apiService.logs.settings.for')">
          <USelect v-model="state.days" :items="days" class="w-48" />
        </UFormField>
        <UAlert icon="i-lucide-shield-check" color="neutral" variant="subtle" :description="t('apiService.logs.settings.never')" />
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('common.save')" color="neutral" :loading="busy" @click="save" />
      </div>
    </template>
  </AppModal>
</template>

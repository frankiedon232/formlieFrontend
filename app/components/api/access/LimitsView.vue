<!--
  Access rules → Rate limits (F13 M3): calls per minute per token, per IP address and per endpoint
  (or no limit). Over a limit, callers get 429 with Retry-After; the answers carry X-RateLimit-Limit
  and X-RateLimit-Remaining. Saving is one click; the change is audited.
-->
<script setup lang="ts">
import type { ApiRateLimits } from '#shared/types/apiService'
import { RATE_LIMIT_CHOICES } from '#shared/utils/apiService/access'

const { t } = useI18n()
const api = useApi()
const { relative, number } = useFormat()
const { busy, run } = useBusy()
// Changing the limits needs api.access (F22 R2 M4); without it they only show
const { can } = useCan()

const limits = ref<ApiRateLimits | null>(null)
const draft = reactive<Record<'per_token' | 'per_ip' | 'per_endpoint', string>>({ per_token: 'off', per_ip: 'off', per_endpoint: 'off' })
const fill = (value: ApiRateLimits) => {
  limits.value = value
  for (const key of ['per_token', 'per_ip', 'per_endpoint'] as const) draft[key] = value[key] == null ? 'off' : String(value[key])
}
onMounted(async () => {
  try {
    fill((await api.get<ApiRateLimits>('/api-service/limits')).data)
  } catch {
    limits.value = null
  }
})
const items = computed(() => RATE_LIMIT_CHOICES.map(value => ({ value: value == null ? 'off' : String(value), label: value == null ? t('apiService.access.limits.none') : t('apiService.access.limits.perMinute', { n: number(value) }) })))
const CARDS = [
  { key: 'per_token', icon: 'i-lucide-key-round' },
  { key: 'per_ip', icon: 'i-lucide-network' },
  { key: 'per_endpoint', icon: 'i-lucide-route' },
] as const
const changed = computed(() => !!limits.value && CARDS.some(card => draft[card.key] !== (limits.value![card.key] == null ? 'off' : String(limits.value![card.key]))))
const save = () =>
  run(
    async () => {
      const body = Object.fromEntries(CARDS.map(card => [card.key, draft[card.key] === 'off' ? null : Number(draft[card.key])]))
      fill((await api.put<ApiRateLimits>('/api-service/limits', body)).data)
    },
    { success: t('apiService.access.limits.saved') },
  )
</script>

<template>
  <UCard variant="outline" class="shrink-0" :ui="{ body: 'flex flex-col gap-4 p-4 sm:p-5' }">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.access.limits.title') }}</h2>
        <p class="text-xs text-muted">{{ t('apiService.access.limits.desc') }}</p>
      </div>
      <span v-if="limits?.updated_at" class="text-xs text-muted">{{ t('apiService.access.limits.changed', { when: relative(limits.updated_at) }) }}</span>
    </div>
    <div v-if="!limits" class="grid gap-3 sm:grid-cols-3"><USkeleton v-for="n in 3" :key="n" class="h-28 rounded-lg" /></div>
    <div v-else class="grid gap-3 sm:grid-cols-3">
      <div v-for="card in CARDS" :key="card.key" class="flex h-full flex-col gap-3 rounded-lg border border-default p-3">
        <div class="flex items-center gap-2">
          <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="card.icon" class="size-4 text-muted" /></span>
          <span class="text-sm font-semibold text-highlighted">{{ t(`apiService.access.limits.${card.key}`) }}</span>
        </div>
        <p class="text-xs text-muted">{{ t(`apiService.access.limits.${card.key}Hint`) }}</p>
        <USelect v-model="draft[card.key]" :items="items" :disabled="!can('api.access')" class="mt-auto w-full" :aria-label="t(`apiService.access.limits.${card.key}`)" />
      </div>
    </div>
    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-xs text-muted">{{ t('apiService.access.limits.answer') }}</p>
      <UButton v-if="can('api.access')" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="busy" :disabled="!changed" @click="save" />
    </div>
  </UCard>
</template>

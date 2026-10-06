<!--
  Tokens & headers → Headers (F13 M2): the headers every caller sends (and when), the organisation's
  address key with Rotate (the old key keeps working for a grace period), and the endpoints that
  require headers of their own (set in the endpoint's Methods step), each with Edit.
-->
<script setup lang="ts">
import type { ApiEndpoint, ApiServiceSettings } from '#shared/types/apiService'

const props = defineProps<{ settings: ApiServiceSettings | null }>()
const emit = defineEmits<{ rotateKey: [] }>()
const { t } = useI18n()
const api = useApi()
const { dateTime, relative } = useFormat()

const endpoints = ref<ApiEndpoint[] | null>(null)
onMounted(async () => {
  try {
    endpoints.value = (await api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' })).data.filter(item => item.required_headers.length)
  } catch {
    endpoints.value = []
  }
})
const STANDARD = [
  { name: 'Authorization', value: 'Bearer <token>', when: 'always' },
  { name: 'Content-Type', value: 'application/json', when: 'body' },
  { name: 'Idempotency-Key', value: '<unique id>', when: 'post' },
  { name: 'X-Formalie-Timestamp', value: '<unix seconds>', when: 'signing' },
  { name: 'X-Formalie-Signature', value: 'sha256=<hmac>', when: 'signing' },
] as const
const base = computed(() => (props.settings ? `${props.settings.base_url}/${props.settings.api_key}` : ''))
</script>

<template>
  <div class="grid shrink-0 gap-4 lg:grid-cols-3">
    <UCard variant="outline" class="min-w-0 lg:col-span-2" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.headers.standardTitle') }}</h2>
        <p class="text-xs text-muted">{{ t('apiService.headers.standardDesc') }}</p>
      </div>
      <ul class="divide-y divide-default overflow-hidden rounded-lg border border-default">
        <li v-for="header in STANDARD" :key="header.name" class="flex flex-col gap-1 px-3 py-2.5 sm:flex-row sm:items-center sm:gap-4">
          <code class="w-48 shrink-0 font-mono text-sm font-medium text-highlighted" dir="ltr">{{ header.name }}</code>
          <code class="min-w-0 flex-1 truncate font-mono text-xs text-muted" dir="ltr">{{ header.value }}</code>
          <UBadge :label="t(`apiService.headers.when.${header.when}`)" color="neutral" :variant="header.when === 'always' ? 'outline' : 'soft'" size="sm" class="w-fit shrink-0 rounded-md" />
        </li>
      </ul>
    </UCard>

    <UCard variant="outline" class="min-w-0" :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-5' }">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.key.title') }}</h2>
        <p class="text-xs text-muted">{{ t('apiService.key.desc') }}</p>
      </div>
      <USkeleton v-if="!settings" class="h-9 w-full" />
      <template v-else>
        <AppCopyField :value="settings.api_key" :label="t('apiService.key.current')" monospace />
        <p class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ base }}/…</p>
        <UAlert v-if="settings.previous_key && settings.previous_until" icon="i-lucide-refresh-cw" color="warning" variant="subtle" :title="t('apiService.key.previous', { key: settings.previous_key, until: dateTime(settings.previous_until) })" />
        <p v-else-if="settings.rotated_at" class="text-xs text-muted">{{ t('apiService.key.rotatedAt', { when: relative(settings.rotated_at) }) }}</p>
        <UButton :label="t('apiService.key.rotate')" icon="i-lucide-refresh-cw" color="neutral" variant="outline" class="mt-auto w-fit" @click="emit('rotateKey')" />
      </template>
    </UCard>

    <UCard variant="outline" class="min-w-0 lg:col-span-3" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
      <div>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.headers.customTitle') }}</h2>
        <p class="text-xs text-muted">{{ t('apiService.headers.customDesc') }}</p>
      </div>
      <div v-if="!endpoints" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 2" :key="n" class="h-16 rounded-lg" /></div>
      <AppEmpty v-else-if="!endpoints.length" size="xs" icon="i-lucide-heading" :title="t('apiService.headers.none')" :description="t('apiService.headers.noneDesc')" />
      <div v-else class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        <div v-for="endpoint in endpoints" :key="endpoint.id" class="flex h-full flex-col gap-2 rounded-lg border border-default p-3">
          <div class="flex items-center justify-between gap-2">
            <NuxtLink :to="{ path: '/api-service/endpoints', query: { endpoint: endpoint.id } }" class="truncate font-mono text-sm font-semibold text-highlighted hover:underline" dir="ltr">/{{ endpoint.name }}</NuxtLink>
            <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" variant="ghost" size="xs" :to="`/api-service/endpoints/${endpoint.id}/edit`" />
          </div>
          <div class="mt-auto flex flex-wrap gap-1">
            <UBadge v-for="name in endpoint.required_headers" :key="name" :label="name" color="neutral" variant="outline" size="sm" class="rounded-md font-mono" />
          </div>
        </div>
      </div>
    </UCard>
  </div>
</template>

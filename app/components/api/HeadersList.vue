<!--
  Tokens & headers → Headers → endpoints with headers of their own (owner, 2026-10-06): grouped by
  service, every endpoint that requires its own headers, each header with its value masked, an eye
  to see it and Copy; the endpoints of a service without own headers are counted, not hidden. Each
  endpoint opens its panel or its Methods step (Edit) to change them.
-->
<script setup lang="ts">
import type { ApiEndpoint, ApiEndpointDetail, ApiService } from '#shared/types/apiService'

const { t } = useI18n()
const api = useApi()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()

const groups = ref<{ service: ApiService; withHeaders: ApiEndpointDetail[]; without: number }[] | null>(null)
async function load() {
  try {
    const [services, endpoints] = await Promise.all([api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' }, { background: true }), api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' }, { background: true })])
    const details = await Promise.all(endpoints.data.filter(item => item.required_headers.length).map(item => api.get<ApiEndpointDetail>(`/api-endpoints/${item.id}`, undefined, { background: true })))
    groups.value = services.data
      .map(service => ({
        service,
        withHeaders: details.map(item => item.data).filter(item => item.service.id === service.id),
        without: endpoints.data.filter(item => item.service.id === service.id && !item.required_headers.length).length,
      }))
      .filter(group => group.withHeaders.length || group.without)
  } catch {
    groups.value = []
  }
}
onMounted(load)
const total = computed(() => (groups.value ?? []).reduce((sum, group) => sum + group.withHeaders.length, 0))

const shown = ref(new Set<string>())
const keyOf = (endpoint: ApiEndpointDetail, name: string) => `${endpoint.id}:${name}`
function toggle(endpoint: ApiEndpointDetail, name: string) {
  const key = keyOf(endpoint, name)
  const next = new Set(shown.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  shown.value = next
}
function copyValue(value: string) {
  void copy(value)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div v-if="!groups" class="grid gap-2 sm:grid-cols-2"><USkeleton v-for="n in 2" :key="n" class="h-24 rounded-lg" /></div>
    <AppEmpty v-else-if="!total" size="xs" icon="i-lucide-heading" :title="t('apiService.headers.none')" :description="t('apiService.headers.noneDesc')" />
    <template v-else>
      <section v-for="group in groups.filter(item => item.withHeaders.length)" :key="group.service.id" class="flex flex-col gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <UIcon name="i-lucide-boxes" class="size-4 text-muted" />
          <NuxtLink :to="{ path: '/api-service/services', query: { service: group.service.id } }" class="text-sm font-semibold text-highlighted hover:underline">{{ group.service.name }}</NuxtLink>
          <UBadge :label="t('apiService.headers.withOwn', { n: group.withHeaders.length }, group.withHeaders.length)" color="neutral" variant="soft" size="sm" class="rounded-md" />
          <span v-if="group.without" class="text-xs text-muted">{{ t('apiService.headers.withoutOwn', { n: group.without }, group.without) }}</span>
        </div>
        <div class="grid gap-2 lg:grid-cols-2">
          <div v-for="endpoint in group.withHeaders" :key="endpoint.id" class="flex h-full flex-col gap-2 rounded-lg border border-default p-3">
            <div class="flex items-center justify-between gap-2">
              <div class="flex min-w-0 items-center gap-2">
                <NuxtLink :to="{ path: '/api-service/endpoints', query: { endpoint: endpoint.id } }" class="truncate font-mono text-sm font-semibold text-highlighted hover:underline" dir="ltr">/{{ endpoint.name }}</NuxtLink>
                <ApiMethods :methods="endpoint.methods" size="xs" />
              </div>
              <UButton :label="t('apiService.actions.edit')" icon="i-lucide-pencil" color="neutral" variant="ghost" size="xs" :to="`/api-service/endpoints/${endpoint.id}/edit`" />
            </div>
            <ul class="flex flex-col divide-y divide-default rounded-md border border-default">
              <li v-for="header in endpoint.headers" :key="header.name" class="flex min-w-0 items-center gap-2 px-2.5 py-1.5">
                <code class="w-36 shrink-0 truncate font-mono text-xs font-medium text-highlighted" dir="ltr">{{ header.name }}</code>
                <code class="min-w-0 flex-1 truncate font-mono text-xs text-muted" dir="ltr">{{ shown.has(keyOf(endpoint, header.name)) ? header.value : header.preview }}</code>
                <UButton :icon="shown.has(keyOf(endpoint, header.name)) ? 'i-lucide-eye-off' : 'i-lucide-eye'" color="neutral" variant="ghost" size="xs" square :aria-label="shown.has(keyOf(endpoint, header.name)) ? t('apiService.headers.hide') : t('apiService.headers.show')" @click="toggle(endpoint, header.name)" />
                <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square :aria-label="t('common.copy')" @click="copyValue(header.value)" />
              </li>
            </ul>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<!--
  Tokens & headers → Headers → every endpoint and the headers its calls need (owner, 2026-10-06),
  slim: one bordered list per service, one row per endpoint. Its own headers (set in its Methods
  step) inline with the value masked, an eye to see it and Copy; the standard ones as small chips
  (Authorization always, Content-Type and Formalie-Key when it takes bodies, the signing headers
  when a token that signs its calls may call it); add or edit its own headers from the row.
-->
<script setup lang="ts">
import type { ApiEndpoint, ApiEndpointDetail, ApiService } from '#shared/types/apiService'

const { t } = useI18n()
const api = useApi()
const { copy } = useClipboard({ legacy: true })
const toast = useToast()

const groups = ref<{ service: ApiService; endpoints: ApiEndpointDetail[] }[] | null>(null)
async function load() {
  try {
    const [services, endpoints] = await Promise.all([api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' }, { background: true }), api.list<ApiEndpoint>('/api-endpoints', { page_size: 100, sort: 'name' }, { background: true })])
    const details = (await Promise.all(endpoints.data.map(item => api.get<ApiEndpointDetail>(`/api-endpoints/${item.id}`, undefined, { background: true })))).map(item => item.data)
    groups.value = services.data.map(service => ({ service, endpoints: details.filter(item => item.service.id === service.id) })).filter(group => group.endpoints.length)
  } catch {
    groups.value = []
  }
}
onMounted(load)
const withOwn = computed(() => (groups.value ?? []).reduce((sum, group) => sum + group.endpoints.filter(item => item.headers.length).length, 0))

/** The standard headers this endpoint's calls carry, and when. */
function standard(endpoint: ApiEndpointDetail) {
  const writes = endpoint.methods.some(method => method === 'POST' || method === 'PUT')
  return [
    { name: 'Authorization', when: 'always' },
    ...(writes ? [{ name: 'Content-Type', when: 'body' }] : []),
    ...(endpoint.methods.includes('POST') ? [{ name: 'Formalie-Key', when: 'post' }] : []),
    ...(endpoint.setup.signing_tokens ? [{ name: 'X-Formalie-Timestamp', when: 'signing' }, { name: 'X-Formalie-Signature', when: 'signing' }] : []),
  ]
}

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
const editLabel = (endpoint: ApiEndpointDetail) => (endpoint.headers.length ? t('apiService.actions.edit') : t('apiService.headers.addOwn'))
</script>

<template>
  <div class="flex flex-col gap-2.5">
    <div v-if="!groups" class="flex flex-col gap-2"><USkeleton v-for="n in 4" :key="n" class="h-10 rounded-lg" /></div>
    <AppEmpty v-else-if="!groups.length" size="xs" icon="i-lucide-route" :title="t('apiService.emptyEndpoints')" :description="t('apiService.emptyEndpointsDesc')" />
    <template v-else>
      <p class="text-xs text-muted">{{ withOwn ? t('apiService.headers.ownCount', { n: withOwn }, withOwn) : t('apiService.headers.noneOwn') }}</p>
      <section v-for="group in groups" :key="group.service.id" class="overflow-hidden rounded-lg border border-default">
        <div class="flex items-center gap-2 border-b border-default bg-elevated/40 px-3 py-1.5">
          <UIcon name="i-lucide-boxes" class="size-3.5 text-muted" />
          <NuxtLink :to="{ path: '/api-service/services', query: { service: group.service.id } }" class="truncate text-xs font-semibold text-highlighted hover:underline">{{ group.service.name }}</NuxtLink>
          <span class="text-[11px] text-muted tabular-nums">· {{ group.endpoints.length }}</span>
        </div>
        <ul class="divide-y divide-default">
          <li v-for="endpoint in group.endpoints" :key="endpoint.id" class="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2">
            <div class="flex min-w-0 items-center gap-2 sm:w-64">
              <NuxtLink :to="{ path: '/api-service/endpoints', query: { endpoint: endpoint.id } }" class="truncate font-mono text-xs font-semibold text-highlighted hover:underline" dir="ltr">/{{ endpoint.name }}</NuxtLink>
              <ApiMethods :methods="endpoint.methods" size="xs" class="shrink-0" />
            </div>
            <div class="flex min-w-0 flex-1 flex-wrap items-center gap-1">
              <span v-for="header in endpoint.headers" :key="header.name" class="inline-flex max-w-full items-center gap-1 rounded-md border border-default py-0.5 ps-1.5 pe-0.5 font-mono text-[11px]" dir="ltr">
                <span class="font-medium text-highlighted">{{ header.name }}</span>
                <span class="max-w-40 truncate text-muted">{{ shown.has(keyOf(endpoint, header.name)) ? header.value : header.preview }}</span>
                <UButton :icon="shown.has(keyOf(endpoint, header.name)) ? 'i-lucide-eye-off' : 'i-lucide-eye'" color="neutral" variant="ghost" size="xs" square class="size-5 p-0.5" :aria-label="shown.has(keyOf(endpoint, header.name)) ? t('apiService.headers.hide') : t('apiService.headers.show')" @click="toggle(endpoint, header.name)" />
                <UButton icon="i-lucide-copy" color="neutral" variant="ghost" size="xs" square class="size-5 p-0.5" :aria-label="t('common.copy')" @click="copyValue(header.value)" />
              </span>
              <UTooltip v-for="header in standard(endpoint)" :key="header.name" :text="t(`apiService.headers.when.${header.when}`)">
                <span class="rounded-md px-1.5 py-0.5 font-mono text-[11px] text-muted" :class="header.when === 'always' ? 'bg-elevated' : 'bg-elevated/50'" dir="ltr">{{ header.name }}</span>
              </UTooltip>
            </div>
            <UTooltip :text="editLabel(endpoint)">
              <UButton :icon="endpoint.headers.length ? 'i-lucide-pencil' : 'i-lucide-plus'" color="neutral" variant="ghost" size="xs" square :aria-label="editLabel(endpoint)" :to="`/api-service/endpoints/${endpoint.id}/edit`" />
            </UTooltip>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

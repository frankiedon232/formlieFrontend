<!--
  API service → Docs (F13 M5): ready-made documentation per service, built from its endpoints (their
  methods, questions, real answer values and required headers). Pick a service in the header; the
  endpoints sit in a list at the side (a sliding row on phones). Every method has its body or query,
  code in five languages, the answer and Try it (a console that never stores anything). Download
  OpenAPI gives the same as a file for Postman and code generators.
-->
<script setup lang="ts">
import type { ApiEndpoint, ApiEndpointDetail, ApiService } from '#shared/types/apiService'
import { openApiFor } from '#shared/utils/apiService/snippets'
import type { ApiMethod } from '#shared/utils/urls/public'

definePageMeta({ breadcrumb: 'nav.apiDocs' })
const { t } = useI18n()
useHead({ title: () => t('nav.apiDocs') })
const api = useApi()
const route = useRoute()
const router = useRouter()

const services = ref<ApiService[]>([])
const endpoints = ref<ApiEndpointDetail[]>([])
const loading = ref(true)
const loadingEndpoints = ref(false)
const failed = ref(false)
const serviceId = computed({
  get: () => (typeof route.query.service === 'string' ? route.query.service : services.value[0]?.id),
  set: id => void router.replace({ query: { service: id } }),
})
const endpointId = computed({
  get: () => (typeof route.query.endpoint === 'string' && endpoints.value.some(item => item.id === route.query.endpoint) ? route.query.endpoint : endpoints.value[0]?.id),
  set: id => void router.replace({ query: { ...route.query, endpoint: id } }),
})
const service = computed(() => services.value.find(item => item.id === serviceId.value) ?? null)
const endpoint = computed(() => endpoints.value.find(item => item.id === endpointId.value) ?? null)
const base = computed(() => (endpoints.value[0]?.url ?? '').replace(/\/[^/]+$/, ''))

async function loadServices() {
  loading.value = true
  failed.value = false
  try {
    services.value = (await api.list<ApiService>('/api-services', { page_size: 100, sort: 'name' })).data
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
async function loadEndpoints(id: string) {
  loadingEndpoints.value = true
  try {
    const list = (await api.list<ApiEndpoint>('/api-endpoints', { 'filter[service]': id, page_size: 100, sort: 'name' })).data
    const details = await Promise.all(list.map(item => api.get<ApiEndpointDetail>(`/api-endpoints/${item.id}`)))
    if (serviceId.value === id) endpoints.value = details.map(item => item.data)
  } catch (error) {
    useErrorHandler().handle(error)
  } finally {
    loadingEndpoints.value = false
  }
}
onMounted(loadServices)
watch(serviceId, id => id && void loadEndpoints(id), { immediate: true })

const serviceItems = computed(() => services.value.map(item => ({ label: item.name, value: item.id })))
const { busy, run } = useBusy()
const download = () =>
  run(
    async () => {
      if (!service.value) return
      const link = document.createElement('a')
      link.href = URL.createObjectURL(new Blob([JSON.stringify(openApiFor(service.value, endpoints.value), null, 2)], { type: 'application/json' }))
      link.download = `${service.value.name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}-openapi.json`
      link.click()
      setTimeout(() => URL.revokeObjectURL(link.href), 1000)
    },
    { success: t('apiService.docs.downloaded') },
  )

const consoleOpen = ref(false)
const consoleMethod = ref<ApiMethod | null>(null)
function tryIt(method: ApiMethod) {
  consoleMethod.value = method
  consoleOpen.value = true
}
</script>

<template>
  <AppPanel id="api-docs" :title="t('nav.apiDocs')" :subtitle="t('apiService.section.docs')" subtitle-icon="i-lucide-book-open">
    <template #actions>
      <USelectMenu v-if="services.length" v-model="serviceId" :items="serviceItems" value-key="value" :search-input="false" icon="i-lucide-boxes" color="neutral" variant="outline" class="w-40 sm:w-56" :aria-label="t('apiService.col.service')" />
      <UButton :label="t('apiService.docs.openapi')" icon="i-lucide-download" color="neutral" variant="outline" :loading="busy" :disabled="!endpoints.length" :ui="{ label: 'hidden sm:inline' }" @click="download" />
    </template>

    <div v-if="loading" class="grid gap-6 lg:grid-cols-[14rem_1fr]">
      <USkeleton class="hidden h-64 lg:block" />
      <div class="flex flex-col gap-4"><USkeleton class="h-24" /><USkeleton class="h-48" /><USkeleton class="h-72" /></div>
    </div>
    <AppEmpty v-else-if="failed" icon="i-lucide-cloud-off" :title="t('apiService.docs.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-rotate-cw', onClick: loadServices }]" />
    <AppEmpty v-else-if="!services.length" icon="i-lucide-boxes" :title="t('apiService.emptyServices')" :description="t('apiService.emptyServicesDesc')" :actions="[{ label: t('nav.apiServices'), icon: 'i-lucide-arrow-right', to: '/api-service/services' }]" />
    <AppEmpty v-else-if="!loadingEndpoints && !endpoints.length" icon="i-lucide-plug" :title="t('apiService.emptyEndpoints')" :description="t('apiService.emptyEndpointsDesc')" :actions="[{ label: t('apiService.actions.newEndpoint'), icon: 'i-lucide-plus', to: '/api-service/endpoints/new' }]" />

    <div v-else class="grid gap-6 lg:grid-cols-[14rem_1fr]" :class="loadingEndpoints ? 'opacity-60' : ''">
      <nav class="flex gap-1 overflow-x-auto pb-1 lg:sticky lg:top-0 lg:flex-col lg:self-start lg:overflow-visible" :aria-label="t('nav.apiEndpoints')">
        <UButton
          v-for="item in endpoints"
          :key="item.id"
          color="neutral"
          :variant="item.id === endpointId ? 'soft' : 'ghost'"
          class="shrink-0 justify-between rounded-full lg:rounded-md"
          :aria-current="item.id === endpointId ? 'page' : undefined"
          @click="endpointId = item.id"
        >
          <span class="truncate font-mono text-xs" dir="ltr">/{{ item.name }}</span>
          <template #trailing><ApiMethods :methods="item.methods" size="xs" class="hidden lg:flex" /></template>
        </UButton>
      </nav>

      <div class="flex min-w-0 flex-col gap-6">
        <template v-if="endpoint">
          <header class="flex flex-col gap-1">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="font-mono text-lg font-semibold text-highlighted" dir="ltr">/{{ endpoint.name }}</h2>
              <DataStatusBadge :status="endpoint.status" />
            </div>
            <p class="text-sm text-muted">{{ endpoint.description || t('apiService.docs.fromForm', { form: endpoint.form.name }) }}</p>
            <AppCopyField :value="endpoint.url" monospace class="mt-2" />
          </header>
          <UAlert v-if="endpoint.headers.length" icon="i-lucide-heading" color="neutral" variant="subtle" :title="t('apiService.docs.headers')" :description="endpoint.headers.map(header => header.name).join(' · ')" />
          <ApiDocsMethod v-for="method in endpoint.methods" :key="`${endpoint.id}-${method}`" :endpoint="endpoint" :method="method" @try="tryIt" />
        </template>
        <ApiDocsGuide :base="base" :endpoint="endpoint" />
      </div>
    </div>

    <ApiDocsConsole v-model:open="consoleOpen" :endpoint="endpoint" :method="consoleMethod" />
  </AppPanel>
</template>

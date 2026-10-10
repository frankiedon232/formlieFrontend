<!--
  API service → Docs & testing (F13 M5; redesigned in M7, owner 2026-10-06). Ready-made docs per
  service, built from its endpoints. Wide screens: a sticky navigation on the left (getting started,
  every endpoint and its methods in their colours, the part on screen marked) and the docs on the
  right: the service at the top (address, how to sign in, live endpoints), getting started, then
  each endpoint and its methods, text beside a dark code panel. Smaller screens: a sliding row of
  endpoints instead of the navigation. Try it opens a drawer that runs real checks with a test token
  and never stores anything; Download OpenAPI gives the same as a file (Postman, code generators).
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
// How this service's endpoints sign in, from the tokens that may call them (owner, 2026-10-06: two ways, never both)
const callers = useCallerToken()
void callers.load(true)
const signIn = computed(() => {
  const kinds = endpoints.value.map(endpoint => callers.kindsFor(endpoint, endpoint.methods))
  const found = (['static', 'client'] as const).filter(kind => kinds.some(item => item[kind].length))
  return found.length ? found : (['static'] as const)
})
const loading = ref(true)
const loadingEndpoints = ref(false)
const failed = ref(false)
const serviceId = computed({
  get: () => (typeof route.query.service === 'string' ? route.query.service : services.value[0]?.id),
  set: id => void router.replace({ query: { service: id } }),
})
const service = computed(() => services.value.find(item => item.id === serviceId.value) ?? null)
const base = computed(() => (endpoints.value[0]?.url ?? '').replace(/\/[^/]+$/, ''))
const live = computed(() => endpoints.value.filter(item => item.status === 'active').length)

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

// Where you are: the section on screen (scroll spy) and jumping to one
const active = ref<string | null>(null)
let observer: IntersectionObserver | null = null
const visible = new Set<string>()
function observe() {
  observer?.disconnect()
  visible.clear()
  observer = new IntersectionObserver(
    entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) visible.add(entry.target.id)
        else visible.delete(entry.target.id)
      }
      const order = [...document.querySelectorAll<HTMLElement>('[data-docs-section]')].map(el => el.id)
      active.value = order.find(id => visible.has(id)) ?? active.value
    },
    { rootMargin: '-10% 0px -75% 0px' },
  )
  document.querySelectorAll<HTMLElement>('[data-docs-section]').forEach(el => observer!.observe(el))
}
watch([endpoints, loading], () => nextTick(observe), { flush: 'post' })
onBeforeUnmount(() => observer?.disconnect())
/** Scrolls the panel's own scroll area (scrollIntoView stalls inside nested scrolling). */
function go(anchor: string) {
  const target = document.getElementById(anchor)
  if (!target) return
  let box: HTMLElement | null = target.parentElement
  while (box && !/(auto|scroll)/.test(getComputedStyle(box).overflowY)) box = box.parentElement
  if (!box) return target.scrollIntoView({ block: 'start' })
  box.scrollTo({ top: box.scrollTop + target.getBoundingClientRect().top - box.getBoundingClientRect().top - 16 })
  active.value = anchor
}

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

// Trying calls needs api.try (F22 R2 M4); reading the docs only api.view
const { can } = useCan()
const consoleOpen = ref(false)
const consoleEndpoint = ref<ApiEndpointDetail | null>(null)
const consoleMethod = ref<ApiMethod | null>(null)
function tryIt(endpoint: ApiEndpointDetail, method?: ApiMethod) {
  if (!can('api.try')) return
  consoleEndpoint.value = endpoint
  consoleMethod.value = method ?? null
  consoleOpen.value = true
}
</script>

<template>
  <AppPanel id="api-docs" :title="t('nav.apiDocs')" :subtitle="t('apiService.section.docs')" subtitle-icon="i-lucide-book-open">
    <template #actions>
      <USelectMenu v-if="services.length" v-model="serviceId" :items="serviceItems" value-key="value" :search-input="false" icon="i-lucide-boxes" color="neutral" variant="outline" class="w-40 sm:w-56" :aria-label="t('apiService.col.service')" />
      <UButton :label="t('apiService.docs.openapi')" icon="i-lucide-download" color="neutral" variant="outline" :loading="busy" :disabled="!endpoints.length" :ui="{ label: 'hidden sm:inline' }" @click="download" />
    </template>

    <div v-if="loading" class="grid gap-6 xl:grid-cols-[15rem_minmax(0,1fr)]">
      <USkeleton class="hidden h-96 xl:block" />
      <div class="flex flex-col gap-4"><USkeleton class="h-40" /><USkeleton class="h-64" /><USkeleton class="h-64" /></div>
    </div>
    <AppEmpty v-else-if="failed" icon="i-lucide-cloud-off" :title="t('apiService.docs.failed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-rotate-cw', onClick: loadServices }]" />
    <AppEmpty v-else-if="!services.length" icon="i-lucide-boxes" :title="t('apiService.emptyServices')" :description="t('apiService.emptyServicesDesc')" :actions="[{ label: t('apiService.journey.service.action'), icon: 'i-lucide-plus', to: { path: '/api-service/services', query: { new: '1' } } }]" />
    <AppEmpty v-else-if="!loadingEndpoints && !endpoints.length" icon="i-lucide-route" :title="t('apiService.emptyEndpoints')" :description="t('apiService.emptyEndpointsDesc')" :actions="[{ label: t('apiService.actions.newEndpoint'), icon: 'i-lucide-plus', to: { path: '/api-service/endpoints/new', query: serviceId ? { service: serviceId } : {} } }]" />

    <div v-else class="grid gap-6 xl:grid-cols-[15rem_minmax(0,1fr)]" :class="loadingEndpoints ? 'opacity-60' : ''">
      <aside class="hidden xl:block">
        <div class="sticky top-0 max-h-[calc(100dvh-9rem)] overflow-y-auto pe-1">
          <ApiDocsNav :service="service" :endpoints="endpoints" :active="active" @go="go" />
        </div>
      </aside>

      <div class="flex min-w-0 flex-col gap-8">
        <!-- The service -->
        <section id="docs-top" data-docs-section class="relative overflow-hidden rounded-2xl border border-default bg-elevated/30 p-5 sm:p-7">
          <div class="pointer-events-none absolute -end-10 -top-10 size-48 rounded-full bg-(--ui-border) opacity-40 blur-3xl" aria-hidden="true" />
          <div class="relative flex flex-col gap-4">
            <span class="inline-flex w-fit items-center gap-1.5 rounded-full border border-default bg-default px-2.5 py-0.5 text-xs text-muted"><UIcon name="i-lucide-book-open" class="size-3.5" />{{ t('apiService.docs.heroKicker') }}</span>
            <div class="flex flex-col gap-1">
              <h2 class="text-2xl font-semibold tracking-tight text-highlighted sm:text-3xl">{{ service?.name }}</h2>
              <p class="max-w-2xl text-sm text-muted">{{ service?.description || t('apiService.docs.heroText') }}</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <UBadge :label="t('apiService.endpointsCount', { n: endpoints.length }, endpoints.length)" icon="i-lucide-route" color="neutral" variant="outline" class="rounded-full" />
              <UBadge :label="t('apiService.docs.liveCount', { n: live })" icon="i-lucide-rocket" color="neutral" variant="outline" class="rounded-full" />
              <UBadge label="HTTPS · JSON" icon="i-lucide-braces" color="neutral" variant="outline" class="rounded-full" />
              <UBadge v-for="kind in signIn" :key="kind" :label="t(`apiService.tokens.kind.${kind}`)" :icon="kind === 'client' ? 'i-lucide-key-square' : 'i-lucide-key-round'" color="neutral" variant="outline" class="rounded-full" />
            </div>
            <AppCopyField :value="base" monospace class="max-w-2xl" />
            <div class="flex flex-wrap gap-2">
              <UButton v-if="endpoints[0] && can('api.try')" :label="t('apiService.docs.tryFirst')" icon="i-lucide-play" color="neutral" @click="tryIt(endpoints[0]!)" />
              <UButton :label="t('apiService.docs.gettingStarted')" icon="i-lucide-arrow-down" color="neutral" variant="outline" @click="go('guide-address')" />
            </div>
          </div>
        </section>

        <!-- Phones and tablets: the endpoints in a sliding row -->
        <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1 xl:hidden">
          <UButton v-for="item in endpoints" :key="item.id" color="neutral" variant="outline" size="sm" class="shrink-0 rounded-full" @click="go(`ep-${item.id}`)">
            <span class="font-mono text-xs" dir="ltr">/{{ item.name }}</span>
          </UButton>
        </div>

        <!-- Getting started -->
        <div class="flex flex-col gap-4">
          <h2 class="text-lg font-semibold text-highlighted">{{ t('apiService.docs.gettingStarted') }}</h2>
          <ApiDocsGuide :base="base" :endpoint="endpoints[0] ?? null" :endpoints="endpoints" />
        </div>

        <!-- Every endpoint -->
        <div v-for="item in endpoints" :key="item.id" class="flex flex-col gap-4">
          <section :id="`ep-${item.id}`" data-docs-section class="scroll-mt-4 flex flex-col gap-3 border-t border-default pt-6">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div class="flex min-w-0 flex-col gap-1">
                <div class="flex flex-wrap items-center gap-2">
                  <h2 class="font-mono text-xl font-semibold text-highlighted" dir="ltr">/{{ item.name }}</h2>
                  <UBadge :label="item.status === 'active' ? t('apiService.setup.isLive') : t('apiService.setup.notLive')" :color="item.status === 'active' ? 'success' : 'neutral'" variant="subtle" size="sm" class="rounded-md" />
                  <ApiMethods :methods="item.methods" size="xs" />
                </div>
                <p class="text-sm text-muted">{{ item.description || t('apiService.docs.fromForm', { form: item.form.name }) }}</p>
              </div>
              <UButton v-if="can('api.try')" :label="t('apiService.docs.tryIt')" icon="i-lucide-play" color="neutral" variant="outline" size="sm" @click="tryIt(item)" />
            </div>
            <AppCopyField :value="item.url" monospace />
            <UAlert v-if="item.status !== 'active'" icon="i-lucide-flask-conical" color="neutral" variant="subtle" :description="t('apiService.docs.notLiveNote')" />
          </section>
          <div v-for="method in item.methods" :id="`ep-${item.id}-${method}`" :key="method" data-docs-section class="scroll-mt-4">
            <ApiDocsMethod :endpoint="item" :method="method" @try="m => tryIt(item, m)" />
          </div>
        </div>
      </div>
    </div>

    <ApiDocsConsole v-model:open="consoleOpen" :endpoint="consoleEndpoint" :method="consoleMethod" />
  </AppPanel>
</template>

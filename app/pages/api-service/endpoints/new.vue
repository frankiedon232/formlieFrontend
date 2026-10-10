<!--
  New endpoint (F13 M1; guided since M7, owner 2026-10-06). First what an endpoint is and where it
  sits in the setup. Without a service there is nothing to put it in, so the page asks for one first
  (New service opens here and comes back). Then the step-by-step wizard. After saving, the endpoint
  is not live yet and the page shows what it still needs: a token, access rules (optional), a test,
  Go live. `?service=` preselects a service.
-->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'

definePageMeta({
  breadcrumb: 'apiService.wizard.newCrumb',
})
const { t } = useI18n()
const api = useApi()
const route = useRoute()
const router = useRouter()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const setup = useApiSetup()
const { can } = useCan()
useHead({ title: () => t('apiService.wizard.newTitle') })

const service = computed(() => (typeof route.query.service === 'string' ? route.query.service : null))
const dirty = ref(false)
const created = ref<ApiEndpointDetail | null>(null)
onMounted(() => void setup.refresh())
const noService = computed(() => setup.summary.value?.services === 0)
const serviceOpen = ref(false)
const introHidden = useLocalStorage('formalie:api-endpoint-intro-hidden', false)

async function saved(endpoint: ApiEndpointDetail) {
  created.value = endpoint
  useToast().add({ title: t('apiService.toast.endpointCreated', { name: endpoint.name }), color: 'success', icon: 'i-lucide-circle-check' })
  void setup.refresh()
}
const serviceMade = (made: { id: string }) => void router.replace({ query: { ...route.query, service: made.id } })

// After saving: the console and Go live, right here
const consoleOpen = ref(false)
const busy = ref(false)
async function live(on: boolean) {
  if (!created.value || busy.value) return
  busy.value = true
  try {
    await api.patch(`/api-endpoints/${created.value.id}`, { status: on ? 'active' : 'disabled' })
    created.value = (await api.get<ApiEndpointDetail>(`/api-endpoints/${created.value.id}`)).data
    useToast().add({ title: on ? t('apiService.setup.toast.live') : t('apiService.setup.toast.notLive'), color: 'success', icon: 'i-lucide-circle-check' })
    void setup.refresh()
  } catch (error) {
    handle(error)
  } finally {
    busy.value = false
  }
}
onBeforeRouteLeave(async () => (!dirty.value || created.value ? true : await confirm({ title: t('apiService.wizard.leaveTitle'), description: t('apiService.wizard.leaveDesc'), confirmLabel: t('apiService.wizard.leave'), danger: true })))
</script>

<template>
  <AppPanel id="api-endpoint-new" :title="t('apiService.wizard.newTitle')" :subtitle="t('apiService.wizard.newDesc')" subtitle-icon="i-lucide-route">
    <template #actions>
      <UButton v-if="created" :label="t('apiService.setup.openEndpoint')" icon="i-lucide-panel-right-open" color="neutral" :to="{ path: '/api-service/endpoints', query: { endpoint: created.id } }" />
      <UButton v-else :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" to="/api-service/endpoints" />
    </template>

    <!-- Saved: what it still needs -->
    <div v-if="created" class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <div class="flex items-start gap-4 rounded-lg border border-default p-5">
        <span class="flex size-12 shrink-0 items-center justify-center rounded-full bg-inverted text-inverted"><UIcon name="i-lucide-check" class="size-6" /></span>
        <div class="flex min-w-0 flex-col gap-1">
          <h2 class="text-lg font-semibold text-highlighted">{{ t('apiService.setup.createdTitle', { name: created.name }) }}</h2>
          <p class="text-sm text-muted">{{ t('apiService.setup.createdText') }}</p>
          <AppCopyField :value="created.url" monospace class="mt-2" />
        </div>
      </div>
      <ApiEndpointsSetup :endpoint="created" :busy="busy" @test="consoleOpen = true" @live="live" />
      <!-- Also at the bottom, under Go live, where people look last (owner, 2026-10-06) -->
      <div class="flex justify-end">
        <UButton :label="t('apiService.setup.openEndpoint')" icon="i-lucide-panel-right-open" color="neutral" :to="{ path: '/api-service/endpoints', query: { endpoint: created.id } }" />
      </div>
      <ApiDocsConsole v-model:open="consoleOpen" :endpoint="created" />
    </div>

    <!-- No service yet: one is needed first -->
    <div v-else-if="noService" class="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <div class="flex flex-col gap-4 rounded-lg border border-default p-5 sm:p-6">
        <span class="flex size-12 items-center justify-center rounded-xl bg-elevated"><UIcon name="i-lucide-boxes" class="size-6 text-highlighted" /></span>
        <div class="flex flex-col gap-1">
          <h2 class="text-lg font-semibold text-highlighted">{{ t('apiService.gate.title') }}</h2>
          <p class="text-sm text-muted">{{ t('apiService.gate.text') }}</p>
        </div>
        <ApiJourney :summary="setup.summary.value" focus="service" compact :actions="false" />
        <div class="flex flex-wrap gap-2">
          <UButton v-if="can('api.service_create')" :label="t('apiService.gate.action')" icon="i-lucide-plus" color="neutral" @click="serviceOpen = true" />
          <UButton :label="t('nav.apiServices')" color="neutral" variant="outline" to="/api-service/services" />
        </div>
      </div>
      <ApiServicesEditModal v-model:open="serviceOpen" :next="false" @saved="serviceMade" />
    </div>

    <template v-else>
      <div v-if="!introHidden" class="flex flex-col gap-4 rounded-lg border border-default p-4 sm:p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="flex min-w-0 items-start gap-3">
            <span class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-elevated"><UIcon name="i-lucide-route" class="size-5 text-highlighted" /></span>
            <div class="flex min-w-0 flex-col gap-1">
              <h2 class="text-sm font-semibold text-highlighted">{{ t('apiService.intro.title') }}</h2>
              <p class="text-sm text-muted">{{ t('apiService.intro.text') }}</p>
            </div>
          </div>
          <UButton :label="t('apiService.intro.hide')" color="neutral" variant="ghost" size="xs" @click="introHidden = true" />
        </div>
        <ApiJourney :summary="setup.summary.value" focus="endpoint" compact :actions="false" />
      </div>
      <ApiWizard :service="service" @saved="saved" @dirty="value => (dirty = value)" />
    </template>
  </AppPanel>
</template>

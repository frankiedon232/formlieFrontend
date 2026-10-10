<!-- Edit an endpoint (F13 M1): the same steps as New endpoint, every step one click away. -->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'

definePageMeta({
  breadcrumb: 'apiService.wizard.editCrumb',
})
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const confirm = useConfirm()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()

const id = computed(() => String(route.params.id ?? ''))
const endpoint = ref<ApiEndpointDetail | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    endpoint.value = (await api.get<ApiEndpointDetail>(`/api-endpoints/${id.value}`)).data
    setLabel(`/api-service/endpoints/${id.value}`, `/${endpoint.value.name}`)
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
void load()
useHead({ title: () => (endpoint.value ? t('apiService.wizard.editTitle', { name: endpoint.value.name }) : t('nav.apiEndpoints')) })

const dirty = ref(false)
const done = ref(false)
async function saved(result: ApiEndpointDetail) {
  done.value = true
  useToast().add({ title: t('apiService.toast.endpointSaved', { name: result.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await navigateTo({ path: '/api-service/endpoints', query: { endpoint: result.id } })
}
onBeforeRouteLeave(async () => (!dirty.value || done.value ? true : await confirm({ title: t('apiService.wizard.leaveTitle'), description: t('apiService.wizard.leaveDesc'), confirmLabel: t('apiService.wizard.leave'), danger: true })))
</script>

<template>
  <AppPanel id="api-endpoint-edit" :title="endpoint ? t('apiService.wizard.editTitle', { name: endpoint.name }) : t('nav.apiEndpoints')" :subtitle="t('apiService.wizard.editDesc')" subtitle-icon="i-lucide-route">
    <template #actions>
      <UButton :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" :to="{ path: '/api-service/endpoints', query: endpoint ? { endpoint: endpoint.id } : undefined }" />
    </template>
    <AppEmpty
      v-if="failed"
      icon="i-lucide-route-off"
      :title="t('apiService.notFound')"
      :actions="[
        { label: t('common.retry'), icon: 'i-lucide-rotate-cw', color: 'neutral', variant: 'outline', onClick: () => void load() },
        { label: t('nav.apiEndpoints'), icon: 'i-lucide-arrow-left', to: '/api-service/endpoints', color: 'neutral', variant: 'subtle', class: 'rtl:[&_.iconify]:-scale-x-100' },
      ]"
      class="my-auto"
    />
    <div v-else-if="!endpoint" class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]" :aria-label="t('common.loading')">
      <USkeleton class="h-[28rem] rounded-lg" />
      <USkeleton class="h-48 rounded-lg" />
    </div>
    <ApiWizard v-else :endpoint="endpoint" @saved="saved" @dirty="value => (dirty = value)" />
  </AppPanel>
</template>

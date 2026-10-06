<!-- New endpoint (F13 M1): the step-by-step wizard; saving opens the new endpoint's panel. `?service=` preselects a service. -->
<script setup lang="ts">
import type { ApiEndpointDetail } from '#shared/types/apiService'

definePageMeta({ breadcrumb: 'apiService.wizard.newCrumb' })
const { t } = useI18n()
const route = useRoute()
const confirm = useConfirm()
useHead({ title: () => t('apiService.wizard.newTitle') })

const service = computed(() => (typeof route.query.service === 'string' ? route.query.service : null))
const dirty = ref(false)
const done = ref(false)
async function saved(endpoint: ApiEndpointDetail) {
  done.value = true
  useToast().add({ title: t('apiService.toast.endpointCreated', { name: endpoint.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await navigateTo({ path: '/api-service/endpoints', query: { endpoint: endpoint.id } })
}
onBeforeRouteLeave(async () => (!dirty.value || done.value ? true : await confirm({ title: t('apiService.wizard.leaveTitle'), description: t('apiService.wizard.leaveDesc'), confirmLabel: t('apiService.wizard.leave'), danger: true })))
</script>

<template>
  <AppPanel id="api-endpoint-new" :title="t('apiService.wizard.newTitle')" :subtitle="t('apiService.wizard.newDesc')" subtitle-icon="i-lucide-route">
    <template #actions>
      <UButton :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" to="/api-service/endpoints" />
    </template>
    <ApiWizard :service="service" @saved="saved" @dirty="value => (dirty = value)" />
  </AppPanel>
</template>

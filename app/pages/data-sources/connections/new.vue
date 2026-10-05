<!-- Add connection (F12 M1): the step-by-step wizard; saving opens the new connection's panel. -->
<script setup lang="ts">
import type { DataSourceDetail } from '#shared/types/datasources'

definePageMeta({ breadcrumb: 'dataSources.wizard.newCrumb' })
const { t } = useI18n()
const confirm = useConfirm()
const counts = useNavCounts()
useHead({ title: () => t('dataSources.wizard.newTitle') })

const dirty = ref(false)
const done = ref(false)
async function saved(source: DataSourceDetail) {
  done.value = true
  void counts.refresh(true)
  useToast().add({ title: t('dataSources.toast.created', { name: source.name }), color: 'success', icon: 'i-lucide-circle-check' })
  await navigateTo({ path: '/data-sources/connections', query: { connection: source.id } })
}
onBeforeRouteLeave(async () => (!dirty.value || done.value ? true : await confirm({ title: t('dataSources.wizard.leaveTitle'), description: t('dataSources.wizard.leaveDesc'), confirmLabel: t('dataSources.wizard.leave'), danger: true })))
</script>

<template>
  <AppPanel id="connection-new" :title="t('dataSources.wizard.newTitle')" :subtitle="t('dataSources.wizard.newDesc')" subtitle-icon="i-lucide-database">
    <template #actions>
      <UButton :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" to="/data-sources/connections" />
    </template>
    <DatasourcesWizard @saved="saved" @dirty="value => (dirty = value)" />
  </AppPanel>
</template>

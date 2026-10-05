<!-- Edit a connection (F12 M1): the same steps as Add connection, every step one click away. -->
<script setup lang="ts">
import type { DataSourceDetail } from '#shared/types/datasources'

definePageMeta({ breadcrumb: 'dataSources.wizard.editCrumb' })
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const confirm = useConfirm()
const counts = useNavCounts()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()

const id = computed(() => String(route.params.id ?? ''))
const source = ref<DataSourceDetail | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    source.value = (await api.get<DataSourceDetail>(`/datasources/${id.value}`)).data
    setLabel(`/data-sources/connections/${id.value}`, source.value.name)
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
void load()
useHead({ title: () => (source.value ? t('dataSources.wizard.editTitle', { name: source.value.name }) : t('nav.dataConnections')) })

const dirty = ref(false)
const done = ref(false)
async function saved(result: DataSourceDetail) {
  done.value = true
  void counts.refresh(true)
  useToast().add({ title: t('dataSources.toast.saved'), color: 'success', icon: 'i-lucide-circle-check' })
  await navigateTo({ path: '/data-sources/connections', query: { connection: result.id } })
}
onBeforeRouteLeave(async () => (!dirty.value || done.value ? true : await confirm({ title: t('dataSources.wizard.leaveTitle'), description: t('dataSources.wizard.leaveDesc'), confirmLabel: t('dataSources.wizard.leave'), danger: true })))
</script>

<template>
  <AppPanel id="connection-edit" :title="source ? t('dataSources.wizard.editTitle', { name: source.name }) : t('nav.dataConnections')" :subtitle="t('dataSources.wizard.editDesc')" subtitle-icon="i-lucide-database-zap">
    <template #actions>
      <UButton :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" :to="{ path: '/data-sources/connections', query: source ? { connection: source.id } : undefined }" />
    </template>
    <UEmpty
      v-if="failed"
      icon="i-lucide-database-backup"
      :title="t('dataSources.notFound')"
      :actions="[
        { label: t('common.retry'), icon: 'i-lucide-rotate-cw', color: 'neutral', variant: 'outline', onClick: () => void load() },
        { label: t('nav.dataConnections'), icon: 'i-lucide-arrow-left', to: '/data-sources/connections', color: 'neutral', variant: 'subtle', class: 'rtl:[&_.iconify]:-scale-x-100' },
      ]"
      class="my-auto"
    />
    <div v-else-if="!source" class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]" :aria-label="t('common.loading')">
      <USkeleton class="h-[28rem] rounded-lg" />
      <USkeleton class="h-48 rounded-lg" />
    </div>
    <DatasourcesWizard v-else :source="source" @saved="saved" @dirty="value => (dirty = value)" />
  </AppPanel>
</template>

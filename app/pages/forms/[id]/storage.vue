<!--
  Where a form's responses are stored (F12 M2): set up storing them in one of the workspace's
  databases, or change the columns and options of a set-up one. Saving opens the destination's
  panel (and offers to send earlier responses). Admins only, like connections.
-->
<script setup lang="ts">
import type { DestinationDetail, FormStorage, StorageField  } from '#shared/types/destinations'

definePageMeta({ breadcrumb: 'destinations.crumb' })
const { t } = useI18n()
const route = useRoute()
const api = useApi()
const confirm = useConfirm()
const counts = useNavCounts()
const { handle } = useErrorHandler()
const { setLabel } = useBreadcrumbs()

const formId = computed(() => String(route.params.id ?? ''))
const formName = ref('')
const storage = ref<(FormStorage & { fields: StorageField[]; can_manage: boolean }) | null>(null)
const destination = ref<DestinationDetail | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    const [form, store] = await Promise.all([api.get<{ name: string }>(`/forms/${formId.value}`), api.get<FormStorage & { fields: StorageField[]; can_manage: boolean }>(`/forms/${formId.value}/storage`)])
    formName.value = form.data.name
    setLabel(`/forms/${formId.value}`, form.data.name)
    storage.value = store.data
    if (store.data.destination && store.data.can_manage) destination.value = (await api.get<DestinationDetail>(`/destinations/${store.data.destination.id}`)).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
void load()
useHead({ title: () => (formName.value ? `${formName.value} · ${t('destinations.crumb')}` : t('destinations.crumb')) })

const dirty = ref(false)
const done = ref(false)
async function saved(result: DestinationDetail, created: boolean) {
  done.value = true
  void counts.refresh(true)
  useToast().add({ title: created ? t('destinations.toast.created', { table: result.table.name }) : t('destinations.toast.saved'), color: 'success', icon: 'i-lucide-circle-check' })
  await navigateTo({ path: '/data-sources/destinations', query: { destination: result.id, backfill: created && result.not_sent ? '1' : undefined } })
}
onBeforeRouteLeave(async () => (!dirty.value || done.value ? true : await confirm({ title: t('dataSources.wizard.leaveTitle'), description: t('destinations.setup.leaveDesc'), confirmLabel: t('dataSources.wizard.leave'), danger: true })))
</script>

<template>
  <AppPanel id="form-storage" :title="destination ? t('destinations.editTitle') : t('destinations.setupTitle')" :subtitle="formName || undefined" subtitle-icon="i-lucide-file-text">
    <template #actions>
      <UButton :label="t('common.cancel')" icon="i-lucide-x" color="neutral" variant="outline" :to="`/forms/${formId}`" />
    </template>
    <UEmpty
      v-if="failed"
      icon="i-lucide-cloud-alert"
      :title="t('dataView.errorTitle')"
      :actions="[
        { label: t('common.retry'), icon: 'i-lucide-rotate-cw', color: 'neutral', variant: 'outline', onClick: () => void load() },
        { label: t('nav.forms'), icon: 'i-lucide-arrow-left', to: '/forms', color: 'neutral', variant: 'subtle', class: 'rtl:[&_.iconify]:-scale-x-100' },
      ]"
      class="my-auto"
    />
    <div v-else-if="!storage" class="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]" :aria-label="t('common.loading')">
      <USkeleton class="h-[28rem] rounded-lg" />
      <USkeleton class="h-48 rounded-lg" />
    </div>
    <UEmpty v-else-if="!storage.can_manage" icon="i-lucide-shield" :title="t('destinations.adminsOnly')" :description="t('destinations.adminsOnlyDesc')" :actions="[{ label: t('common.back'), icon: 'i-lucide-arrow-left', to: `/forms/${formId}`, color: 'neutral', variant: 'outline', class: 'rtl:[&_.iconify]:-scale-x-100' }]" class="my-auto" />
    <UEmpty v-else-if="!storage.fields.length" icon="i-lucide-file-question" :title="t('destinations.noFields')" :description="t('destinations.noFieldsDesc')" :actions="[{ label: t('forms.detail.edit'), icon: 'i-lucide-pencil-ruler', to: `/forms/${formId}/build`, color: 'neutral' }]" class="my-auto" />
    <DestinationsSetup v-else :form-id="formId" :form-name="formName" :fields="storage.fields" :destination="destination" @saved="saved" @dirty="value => (dirty = value)" />
  </AppPanel>
</template>

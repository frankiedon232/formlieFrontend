<!--
  Forms list (F6; locked list-page format 2026-10-04): two chart cards on top (responses across
  forms, forms by status), then DataView (search, status / folder / owner / tag filters, date
  range, sort, Columns, Table / Grid with the locked card) · inline rename · duplicate · move ·
  tags · lifecycle · delete to Trash · bulk.
  Busy rows while an action runs; every action refreshes the list and the sidebar counts.
-->
<script setup lang="ts">
import type { FormFolder } from '#shared/types/forms'

definePageMeta({ breadcrumb: 'nav.forms' })

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
useHead({ title: () => t('nav.forms') })

const browser = useTemplateRef<{
  refresh: () => Promise<void>
  folders: FormFolder[]
  foldersLoading: boolean
  loadMeta: () => Promise<void>
}>('browser')
const foldersOpen = ref(false)

const STATUS_DOTS: Record<string, string> = {
  draft: 'bg-amber-500',
  published: 'bg-green-500',
  closed: 'bg-violet-600',
  archived: 'bg-(--ui-text-dimmed)',
}
// The status card filters the list (one status at a time; the same status again clears it).
const statusFilter = computed(() =>
  typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null,
)
const filterStatus = (status: string) =>
  void router.replace({
    query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined },
  })

const { can } = useCan()
defineShortcuts({ n: () => can('forms.create') && navigateTo('/forms/new') })
</script>

<template>
  <AppPanel
    id="forms"
    :title="t('nav.forms')"
    :subtitle="t('forms.description')"
    subtitle-icon="i-lucide-refresh-cw"
  >
    <template #actions>
      <UButton
        icon="i-lucide-folder-cog"
        :label="t('forms.folders.button')"
        color="neutral"
        variant="outline"
        @click="foldersOpen = true"
      />
      <UButton
        v-if="can('forms.create')"
        icon="i-lucide-upload"
        :label="t('forms.import')"
        color="neutral"
        variant="outline"
        :to="{ path: '/forms/new', query: { mode: 'import' } }"
      />
      <UButton v-if="can('forms.create')" icon="i-lucide-plus" :label="t('nav.newForm')" color="neutral" to="/forms/new">
        <template #trailing>
          <UKbd value="N" class="hidden lg:inline-flex" />
        </template>
      </UButton>
    </template>

    <div class="flex flex-col gap-4">
      <FormsListOverview :status="statusFilter" :dots="STATUS_DOTS" @status="filterStatus" />
      <FormsListBrowser ref="browser" />
    </div>

    <FormsListFoldersModal
      v-model:open="foldersOpen"
      :folders="browser?.folders ?? []"
      :loading="browser?.foldersLoading ?? false"
      @changed="browser?.refresh()"
    />
  </AppPanel>
</template>

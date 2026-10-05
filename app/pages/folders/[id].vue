<!--
  A folder's page (F11 M4, owner request 2026-10-02): the folder's name and colour in the header with
  Edit, Delete (only when empty) and New form (the folder preselected); two chart cards (responses
  in the last 30 days, forms by status, a status filters the list); then the folder's forms in the
  same list as the Forms page (table / grid, filters, actions), the folder filter fixed.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FolderRow } from '#shared/types/forms'
import { folderColor } from '#shared/utils/forms/folders'

definePageMeta({ breadcrumb: 'nav.folders' })
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const api = useApi()
const confirm = useConfirm()
const counts = useNavCounts()
const { relative } = useFormat()
const { setLabel } = useBreadcrumbs()
const { handle } = useErrorHandler()

const id = computed(() => String(route.params.id ?? ''))
const folder = ref<FolderRow | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    folder.value = (await api.get<FolderRow>(`/folders/${id.value}`)).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
watch(id, () => {
  folder.value = null
  void load()
}, { immediate: true })
watch(() => folder.value?.name, name => name && setLabel(route.path, name))
// Opening a folder brings it to the sidebar (recently opened, per person).
const sidebarFolders = useSidebarFolders()
watch(() => folder.value?.id, folderId => folderId && sidebarFolders.visit(folderId))
useHead({ title: () => folder.value?.name ?? t('nav.folders') })

const STATUS_DOTS: Record<string, string> = { draft: 'bg-amber-500', published: 'bg-green-500', closed: 'bg-violet-600', archived: 'bg-(--ui-text-dimmed)' }
const statusFilter = computed(() => (typeof route.query.status === 'string' && !route.query.status.includes(',') ? route.query.status : null))
const filterStatus = (status: string) => void router.replace({ query: { ...route.query, status: statusFilter.value === status ? undefined : status, page: undefined } })

const editOpen = ref(false)
const { busy, run } = useBusy()
async function remove() {
  if (!folder.value) return
  if (!(await confirm({ title: t('forms.folders.deleteTitle', { name: folder.value.name }), description: t('forms.folders.deleteEmpty'), danger: true }))) return
  const done = await run(() => api.del(`/folders/${id.value}`), { success: t('forms.folders.deleted') })
  if (!done) return
  void counts.refresh(true)
  await navigateTo('/folders')
}
/** Pin / unpin in the sidebar (per person, up to five). */
const pinItem = (folderId: string): DropdownMenuItem =>
  sidebarFolders.isPinned(folderId)
    ? { label: t('folders.unpin'), icon: 'i-lucide-pin-off', onSelect: () => sidebarFolders.togglePin(folderId) }
    : sidebarFolders.canPin.value
      ? { label: t('folders.pin'), icon: 'i-lucide-pin', onSelect: () => sidebarFolders.togglePin(folderId) }
      : { label: t('folders.pinFull'), icon: 'i-lucide-pin', disabled: true }
const menu = computed<DropdownMenuItem[][]>(() => [
  [{ label: t('folders.editTitle'), icon: 'i-lucide-pencil', onSelect: () => (editOpen.value = true) }, ...(folder.value ? [pinItem(folder.value.id)] : [])],
  [
    folder.value?.forms_count
      ? { label: t('forms.folders.notEmpty'), icon: 'i-lucide-trash-2', disabled: true }
      : { label: t('forms.folders.deleteNamed', { name: folder.value?.name ?? '' }), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove() },
  ],
])
const changed = () => Promise.all([load(), counts.refresh(true)])
</script>

<template>
  <AppPanel
    id="folder"
    :title="folder?.name ?? t('nav.folders')"
    :subtitle="folder ? (folder.last_activity_at ? t('folders.subtitle', { n: folder.forms_count, when: relative(folder.last_activity_at) }, folder.forms_count) : t('forms.folders.count', { count: folder.forms_count }, folder.forms_count)) : undefined"
    subtitle-icon="i-lucide-folder"
    :subtitle-icon-class="folder ? folderColor(folder.color).text : undefined"
    :subtitle-icon-style="folder ? folderColor(folder.color).textStyle : undefined"
  >
    <template v-if="folder" #actions>
      <UButton :label="t('folders.editTitle')" icon="i-lucide-pencil" color="neutral" variant="outline" class="hidden sm:inline-flex" @click="editOpen = true" />
      <UDropdownMenu :items="menu" :content="{ align: 'end' }">
        <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" square :loading="busy" :aria-label="t('dataView.actions')" />
      </UDropdownMenu>
      <UButton :label="t('nav.newForm')" icon="i-lucide-plus" color="neutral" :to="{ path: '/forms/new', query: { folder: folder.id } }" />
    </template>

    <AppEmpty
      v-if="failed"
      icon="i-lucide-folder-x"
      :title="t('folders.notFound')"
      :actions="[
        { label: t('common.retry'), icon: 'i-lucide-rotate-cw', color: 'neutral', variant: 'outline', onClick: () => void load() },
        { label: t('nav.foldersAll'), icon: 'i-lucide-arrow-left', to: '/folders', color: 'neutral', variant: 'subtle', class: 'rtl:[&_.iconify]:-scale-x-100' },
      ]"
      class="my-auto"
    />
    <div v-else-if="!folder" class="flex flex-col gap-4" :aria-label="t('common.loading')">
      <div class="grid gap-4 lg:grid-cols-2"><USkeleton v-for="n in 2" :key="n" class="h-40 rounded-lg" /></div>
      <USkeleton class="h-96 rounded-lg" />
    </div>
    <div v-else class="flex flex-col gap-4">
      <div class="flex items-center gap-2 text-sm text-muted sm:hidden">
        <UIcon name="i-lucide-folder" class="size-4" :class="folderColor(folder.color).text" :style="folderColor(folder.color).textStyle" />{{ t('forms.folders.count', { count: folder.forms_count }, folder.forms_count) }}
      </div>
      <FoldersOverview :folder="folder" :status="statusFilter" :dots="STATUS_DOTS" @status="filterStatus" />
      <FormsListBrowser :key="folder.id" :folder-id="folder.id" @changed="changed" />
    </div>

    <FoldersEditModal v-model:open="editOpen" :folder="folder" @saved="changed" />
  </AppPanel>
</template>

<!--
  Dashboard → forms filter (F21 M5): narrow the Workspace and Forms views to one folder and / or one owner. A
  Filter button (with how many are on) opens the two pickers; each choice shows as a chip that clears it. The
  page keeps the choice in the address.
-->
<script setup lang="ts">
import type { FormFacets, FormFolder } from '#shared/types/forms'

const props = defineProps<{ folder?: string; owner?: string }>()
const emit = defineEmits<{ change: [value: { folder?: string; owner?: string }] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const folders = ref<FormFolder[]>([])
const owners = ref<FormFacets['owners']>([])
const loading = ref(true)
onMounted(async () => {
  try {
    const [folderList, facets] = await Promise.all([
      api.get<FormFolder[]>('/folders', undefined, { background: true }),
      api.get<FormFacets>('/forms/facets', undefined, { background: true }),
    ])
    folders.value = folderList.data
    owners.value = facets.data.owners
  } catch (error) {
    handle(error, { silent: true })
  } finally {
    loading.value = false
  }
})

const folderItems = computed(() => [
  { value: 'none', label: t('dashboard.filter.noFolder'), icon: 'i-lucide-folder-x' },
  ...folders.value.map(folder => ({ value: folder.id, label: folder.name, icon: 'i-lucide-folder' })),
])
const ownerItems = computed(() =>
  owners.value.map(owner => ({ value: owner.id, label: owner.name, icon: 'i-lucide-user' })),
)
// While the names load the chips show a placeholder, never the raw id; an unknown id reads as the field's name
const folderLabel = computed(
  () =>
    folderItems.value.find(item => item.value === props.folder)?.label ??
    (loading.value ? null : t('dashboard.filter.folder')),
)
const ownerLabel = computed(
  () =>
    ownerItems.value.find(item => item.value === props.owner)?.label ??
    (loading.value ? null : t('dashboard.filter.owner')),
)
const count = computed(() => Number(!!props.folder) + Number(!!props.owner))

const set = (key: 'folder' | 'owner', value: string | undefined) =>
  emit('change', { folder: props.folder, owner: props.owner, [key]: value || undefined })
</script>

<template>
  <div class="flex min-w-0 flex-wrap items-center gap-2">
    <UPopover :content="{ align: 'start' }">
      <UButton
        icon="i-lucide-list-filter"
        :label="t('dashboard.filter.label')"
        color="neutral"
        variant="outline"
        size="sm"
      >
        <template v-if="count" #trailing>
          <UBadge :label="String(count)" color="neutral" size="sm" />
        </template>
      </UButton>
      <template #content>
        <div class="flex w-72 flex-col gap-3 p-3">
          <UFormField :label="t('dashboard.filter.folder')">
            <USelectMenu
              :model-value="folder"
              :items="folderItems"
              value-key="value"
              :loading="loading"
              :placeholder="t('dashboard.filter.anyFolder')"
              :search-input="{ placeholder: t('common.search') }"
              class="w-full"
              @update:model-value="value => set('folder', value as string)"
            />
          </UFormField>
          <UFormField :label="t('dashboard.filter.owner')">
            <USelectMenu
              :model-value="owner"
              :items="ownerItems"
              value-key="value"
              :loading="loading"
              :placeholder="t('dashboard.filter.anyOwner')"
              :search-input="{ placeholder: t('common.search') }"
              class="w-full"
              @update:model-value="value => set('owner', value as string)"
            />
          </UFormField>
          <UButton
            v-if="count"
            :label="t('dashboard.filter.clear')"
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            class="self-start"
            @click="emit('change', {})"
          />
        </div>
      </template>
    </UPopover>
    <UBadge v-if="folder" color="neutral" variant="outline" size="md" class="max-w-56 gap-1">
      <UIcon name="i-lucide-folder" class="size-3.5 shrink-0" />
      <span v-if="folderLabel" class="truncate">{{ folderLabel }}</span>
      <USkeleton v-else class="h-3 w-16" />
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="link"
        size="xs"
        square
        class="-me-1 p-0"
        :aria-label="t('dashboard.filter.remove', { name: folderLabel ?? t('dashboard.filter.folder') })"
        @click="set('folder', undefined)"
      />
    </UBadge>
    <UBadge v-if="owner" color="neutral" variant="outline" size="md" class="max-w-56 gap-1">
      <UIcon name="i-lucide-user" class="size-3.5 shrink-0" />
      <span v-if="ownerLabel" class="truncate">{{ ownerLabel }}</span>
      <USkeleton v-else class="h-3 w-16" />
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="link"
        size="xs"
        square
        class="-me-1 p-0"
        :aria-label="t('dashboard.filter.remove', { name: ownerLabel ?? t('dashboard.filter.owner') })"
        @click="set('owner', undefined)"
      />
    </UBadge>
  </div>
</template>

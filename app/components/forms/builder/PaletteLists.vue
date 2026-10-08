<!--
  "Lists" palette tab: reusable option lists (countries, regions, products …), each marked plain or
  with its levels (Country → Region → City). Click or drag to add it: a plain list as a dropdown, a
  list with levels as one linked field per level in one row, each narrowing the next. Nothing is set
  while adding (owner 2026-10-07): Show as, one or several, required are set in the right panel.
  ⋯ edits / deletes the list or opens it in List Option. "New list" creates one.
-->
<script setup lang="ts">
import { levelsOf, offeredOptions } from '#shared/utils/forms/options'
import type { DropdownMenuItem } from '@nuxt/ui'
import { VueDraggable } from 'vue-draggable-plus'
import type { OptionList } from '#shared/types/forms'

const props = defineProps<{ query: string }>()
const emit = defineEmits<{ added: [] }>()
const { t } = useI18n()
const { number } = useFormat()
const builder = useBuilder()
const library = useFieldLibrary()
const confirm = useConfirm()

const items = computed(() => {
  const q = props.query.trim().toLowerCase()
  return library.lists.value.filter(list => !q || list.name.toLowerCase().includes(q))
})
const editing = ref<OptionList | null>(null)
const modalOpen = ref(false)
function openEditor(list: OptionList | null) {
  editing.value = list
  modalOpen.value = true
}

function add(list: OptionList) {
  if (builder.placeRow(builder.createListFields(list))) emit('added')
}
const kindOf = (list: OptionList) => {
  const levels = levelsOf(list)
  if (levels) return levels.map(level => level.label).join(' → ')
  const count = list.level_counts ? (list.level_counts[0] ?? 0) : offeredOptions(list).length
  return t('library.optionCount', { count: number(count) }, count)
}
const drag = usePaletteDrag(() => emit('added'))
// Dragging a list with levels carries its top level; the others join it on drop
const clone = (list: OptionList) => {
  const [first, ...others] = builder.createListFields(list)
  return drag.track(first!, others)
}

const busyId = ref<string | null>(null)
async function remove(list: OptionList) {
  if (!(await confirm({ title: t('library.deleteListTitle', { name: list.name }), description: t('library.deleteListDesc'), danger: true, confirmLabel: t('library.deleteList') })))
    return
  busyId.value = list.id
  try {
    await library.removeList(list)
  } finally {
    busyId.value = null
  }
}

const menu = (list: OptionList): DropdownMenuItem[][] => [
  [
    { label: t('library.editList'), icon: 'i-lucide-pencil', onSelect: () => (levelsOf(list) || list.level_counts ? void navigateTo(`/option-sets/${list.id}`) : openEditor(list)) },
    { label: t('library.openInListOption'), icon: 'i-lucide-external-link', onSelect: () => void navigateTo(`/option-sets/${list.id}`) },
    { label: t('library.deleteList'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => void remove(list) },
  ],
]
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2">
    <UButton
      :label="t('library.newList')"
      icon="i-lucide-list-plus"
      color="neutral"
      variant="outline"
      size="sm"
      block
      @click="openEditor(null)"
    />
    <div class="-me-2 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto pe-2">
      <div v-if="library.loading.value && !library.loaded.value" class="flex flex-col gap-1.5" :aria-label="t('common.loading')">
        <USkeleton v-for="i in 4" :key="i" class="h-9 w-full" />
      </div>
      <AppEmpty v-else-if="!library.lists.value.length" size="xs" icon="i-lucide-list" :title="t('library.listsEmptyTitle')" :description="t('library.listsEmptyDesc')" />
      <AppEmpty v-else-if="!items.length" size="xs" icon="i-lucide-search-x" :title="t('builder.palette.none')" />
      <VueDraggable
        v-else
        :model-value="items"
        :group="{ name: 'fields', pull: 'clone', put: false }"
        :clone="clone"
        :sort="false"
        :animation="150"
        :ghost-class="DROP_GHOST"
        filter="[data-no-drag]"
        :prevent-on-filter="false"
        class="flex flex-col gap-0.5"
        @start="drag.start"
        @end="drag.end"
      >
        <div
          v-for="list in items"
          :key="list.id"
          class="flex flex-col rounded-md hover:bg-elevated/60"
          :class="busyId === list.id ? 'pointer-events-none opacity-60' : ''"
        >
          <div class="flex items-center gap-1">
          <UButton
            :icon="levelsOf(list) ? 'i-lucide-network' : 'i-lucide-list'"
            color="neutral"
            variant="ghost"
            size="sm"
            class="min-w-0 flex-1 cursor-grab justify-start gap-2 text-default active:cursor-grabbing"
            @click="add(list)"
          >
            <span class="flex min-w-0 flex-col items-start">
              <span class="flex max-w-full items-center gap-1.5"><span class="truncate">{{ list.name }}</span><UBadge v-if="levelsOf(list)" :label="t('library.levels', { n: levelsOf(list)!.length })" color="neutral" variant="soft" size="sm" class="shrink-0" /><UBadge v-if="list.large" :label="t('optionSets.large.badge')" color="neutral" variant="outline" size="sm" class="shrink-0" /></span>
              <span class="max-w-full truncate text-xs font-normal text-muted">{{ kindOf(list) }}</span>
            </span>
          </UButton>
          <UDropdownMenu :items="menu(list)" :content="{ align: 'end' }">
            <UButton
              :icon="busyId === list.id ? 'i-lucide-loader-circle' : 'i-lucide-ellipsis'"
              color="neutral"
              variant="ghost"
              size="xs"
              square
              data-no-drag
              :class="busyId === list.id ? 'animate-spin' : ''"
              :aria-label="t('library.listMenu', { name: list.name })"
            />
          </UDropdownMenu>
          </div>
        </div>
      </VueDraggable>
    </div>
    <FormsBuilderListModal v-model:open="modalOpen" :list="editing" />
  </div>
</template>

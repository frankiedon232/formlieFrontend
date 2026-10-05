<!--
  "Lists" palette tab: reusable option lists (countries, regions, products …). Click or drag adds
  a dropdown filled with the list; ⋯ adds it as radio buttons / checkboxes / multi-select, or
  edits / deletes the list. "New list" creates one.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { VueDraggable } from 'vue-draggable-plus'
import type { OptionList } from '#shared/types/forms'
import type { FieldType } from '#shared/utils/forms/fields'

const props = defineProps<{ query: string }>()
const emit = defineEmits<{ added: [] }>()
const { t } = useI18n()
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

function add(list: OptionList, type: FieldType = 'dropdown') {
  if (builder.place(builder.createFromList(list, type))) emit('added')
}
const drag = usePaletteDrag(() => emit('added'))
const clone = (list: OptionList) => drag.track(builder.createFromList(list))

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

const AS: FieldType[] = ['dropdown', 'radio', 'checkbox', 'multi_select']
const menu = (list: OptionList): DropdownMenuItem[][] => [
  AS.map(type => ({
    label: t('library.addAs', { type: t(`builder.field.${type}`) }),
    icon: fieldIcon(type),
    onSelect: () => add(list, type),
  })),
  [
    { label: t('library.editList'), icon: 'i-lucide-pencil', onSelect: () => openEditor(list) },
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
          class="flex items-center gap-1 rounded-md hover:bg-elevated/60"
          :class="busyId === list.id ? 'pointer-events-none opacity-60' : ''"
        >
          <UButton
            icon="i-lucide-list"
            color="neutral"
            variant="ghost"
            size="sm"
            class="min-w-0 flex-1 cursor-grab justify-start gap-2 text-default active:cursor-grabbing"
            :aria-label="t('library.addList', { name: list.name })"
            @click="add(list)"
          >
            <span class="flex min-w-0 flex-col items-start">
              <span class="max-w-full truncate">{{ list.name }}</span>
              <span class="text-xs font-normal text-muted">{{ t('library.optionCount', { count: list.options.length }, list.options.length) }}</span>
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
      </VueDraggable>
    </div>
    <FormsBuilderListModal v-model:open="modalOpen" :list="editing" />
  </div>
</template>

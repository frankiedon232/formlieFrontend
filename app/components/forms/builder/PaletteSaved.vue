<!--
  "Saved" palette tab: fields the team saved for reuse (from the field settings → "Save field").
  Click or drag to add a fresh copy; remove one from the library with ⋯ (confirmed).
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import type { SavedField } from '#shared/types/forms'

const props = defineProps<{ query: string }>()
const emit = defineEmits<{ added: [] }>()
const { t } = useI18n()
const builder = useBuilder()
const library = useFieldLibrary()
const confirm = useConfirm()

const items = computed(() => {
  const q = props.query.trim().toLowerCase()
  return library.savedFields.value.filter(
    item => !q || item.name.toLowerCase().includes(q) || t(`builder.field.${item.field.type}`).toLowerCase().includes(q),
  )
})

function add(item: SavedField) {
  if (builder.place(builder.createFromSaved(item))) emit('added')
}
const drag = usePaletteDrag(() => emit('added'))
const clone = (item: SavedField) => drag.track(builder.createFromSaved(item))

const removing = ref<string | null>(null)
async function remove(item: SavedField) {
  if (!(await confirm({ title: t('library.removeFieldTitle', { name: item.name }), description: t('library.removeFieldDesc'), danger: true, confirmLabel: t('library.remove') })))
    return
  removing.value = item.id
  try {
    await library.removeField(item)
  } finally {
    removing.value = null
  }
}
</script>

<template>
  <div class="-me-2 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto pe-2">
    <div v-if="library.loading.value && !library.loaded.value" class="flex flex-col gap-1.5" :aria-label="t('common.loading')">
      <USkeleton v-for="i in 4" :key="i" class="h-9 w-full" />
    </div>
    <div v-else-if="!library.savedFields.value.length" class="flex flex-col items-center gap-2 px-2 py-8 text-center">
      <UIcon name="i-lucide-bookmark" class="size-6 text-muted" />
      <p class="text-sm font-medium text-highlighted">{{ t('library.savedEmptyTitle') }}</p>
      <p class="text-xs text-muted">{{ t('library.savedEmptyDesc') }}</p>
    </div>
    <p v-else-if="!items.length" class="px-1 text-sm text-muted">{{ t('builder.palette.none') }}</p>
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
        v-for="item in items"
        :key="item.id"
        class="group/saved flex items-center gap-1 rounded-md hover:bg-elevated/60"
        :class="removing === item.id ? 'pointer-events-none opacity-60' : ''"
      >
        <UButton
          :icon="fieldIcon(item.field.type)"
          color="neutral"
          variant="ghost"
          size="sm"
          class="min-w-0 flex-1 cursor-grab justify-start gap-2 text-default active:cursor-grabbing"
          :aria-label="t('builder.palette.add', { field: item.name })"
          @click="add(item)"
        >
          <span class="flex min-w-0 flex-col items-start">
            <span class="max-w-full truncate">{{ item.name }}</span>
            <span class="max-w-full truncate text-xs font-normal text-muted">{{ t(`builder.field.${item.field.type}`) }}</span>
          </span>
        </UButton>
        <UButton
          :icon="removing === item.id ? 'i-lucide-loader-circle' : 'i-lucide-trash-2'"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          data-no-drag
          :class="removing === item.id ? 'animate-spin' : 'opacity-0 group-hover/saved:opacity-100 focus-visible:opacity-100'"
          :aria-label="t('library.removeField', { name: item.name })"
          @click="remove(item)"
        />
      </div>
    </VueDraggable>
  </div>
</template>

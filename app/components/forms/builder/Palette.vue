<!--
  Field palette (FRONTEND-SPEC §6, left pane), three tabs in the design's segmented control:
  Fields (new fields by category) · Saved (fields saved for reuse) · Lists (option lists that
  become a choice field). One search box for the active tab. Click / Enter adds after the
  selected field (or at the end); drag drops it exactly where you want.
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import { FIELD_CATEGORIES, FIELD_TYPES, type FieldType } from '#shared/utils/forms/fields'

const emit = defineEmits<{ added: [] }>()
const { t } = useI18n()
const builder = useBuilder()
const library = useFieldLibrary()
const query = ref('')
const tab = ref<'fields' | 'saved' | 'lists'>('fields')
onMounted(() => library.load())

const tabs = computed(() => [
  { value: 'fields', label: t('library.tab.fields') },
  // Saved fields only for people who may see them (F22 R2 M3)
  ...(useCan().can('fields.view') ? [{ value: 'saved' as const, label: t('library.tab.saved'), badge: library.savedFields.value.length || undefined }] : []),
  { value: 'lists', label: t('library.tab.lists'), badge: library.lists.value.length || undefined },
])

const groups = computed(() => {
  const q = query.value.trim().toLowerCase()
  return FIELD_CATEGORIES.map(category => ({
    category,
    items: (Object.keys(FIELD_TYPES) as FieldType[])
      .filter(type => FIELD_TYPES[type].category === category)
      .map(type => ({ type, label: t(`builder.field.${type}`), soon: 'soon' in FIELD_TYPES[type] }))
      .filter(item => !q || item.label.toLowerCase().includes(q) || item.type.includes(q)),
  })).filter(group => group.items.length)
})

function add(type: FieldType) {
  if (builder.addField(type)) emit('added')
}

// Drag from the palette: the canvas receives a fresh field (clone), the palette never changes.
const drag = usePaletteDrag(() => emit('added'))
const cloneField = (item: { type: FieldType }) => drag.track(builder.createField(item.type))
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <UTabs
      v-model="tab"
      :items="tabs"
      :content="false"
      color="neutral"
      size="xs"
      :ui="{ ...SEGMENTED_UI, list: `${SEGMENTED_UI.list} w-full`, trigger: `${SEGMENTED_UI.trigger} flex-1 px-1.5`, trailingBadge: 'px-1' }"
      :aria-label="t('library.tabsLabel')"
      class="w-full"
    />
    <UInput
      v-model="query"
      icon="i-lucide-search"
      :placeholder="tab === 'fields' ? t('builder.palette.search') : tab === 'saved' ? t('library.searchSaved') : t('library.searchLists')"
      size="sm"
      class="w-full"
      :aria-label="t('builder.palette.search')"
    />

    <div v-if="tab === 'fields'" class="-me-2 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pe-2">
      <section v-for="group in groups" :key="group.category">
        <h3 class="mb-1 px-1 text-xs font-medium text-muted uppercase">
          {{ t(`builder.category.${group.category}`) }}
        </h3>
        <VueDraggable
          :model-value="group.items"
          :group="{ name: 'fields', pull: 'clone', put: false }"
          :clone="cloneField"
          :sort="false"
          :animation="150"
          :ghost-class="DROP_GHOST"
          filter="[data-soon]"
          class="grid grid-cols-1 gap-0.5"
          @start="drag.start"
          @end="drag.end"
        >
          <UButton
            v-for="item in group.items"
            :key="item.type"
            :icon="fieldIcon(item.type)"
            color="neutral"
            variant="ghost"
            size="sm"
            class="w-full justify-start gap-2 text-default"
            :class="item.soon ? 'opacity-60' : 'cursor-grab active:cursor-grabbing'"
            :disabled="item.soon"
            :data-soon="item.soon || undefined"
            :aria-label="t('builder.palette.add', { field: item.label })"
            @click="add(item.type)"
          >
            <span class="truncate">{{ item.label }}</span>
            <UBadge v-if="item.soon" :label="t('builder.soon')" color="neutral" variant="outline" size="sm" class="ms-auto" />
          </UButton>
        </VueDraggable>
      </section>
      <AppEmpty v-if="!groups.length" size="xs" icon="i-lucide-search-x" :title="t('builder.palette.none')" />
    </div>

    <FormsBuilderPaletteSaved v-else-if="tab === 'saved'" :query="query" @added="emit('added')" />
    <FormsBuilderPaletteLists v-else :query="query" @added="emit('added')" />
  </div>
</template>

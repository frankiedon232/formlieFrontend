<!--
  Field palette (FRONTEND-SPEC §6, left pane): search + categories. Click / Enter adds the field
  after the selected one (or at the end); drag drops it exactly where you want (drag + keyboard).
  Look: muted uppercase group labels and icon rows, like the sidebar (docs/design).
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import { FIELD_CATEGORIES, FIELD_TYPES, type FieldType } from '#shared/utils/forms/fields'

const emit = defineEmits<{ added: [] }>()
const { t } = useI18n()
const builder = useBuilder()
const query = ref('')

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
let dragged: string | null = null
const cloneField = (item: { type: FieldType }) => {
  const field = builder.createField(item.type)
  dragged = field.id
  return field
}
function onEnd() {
  if (dragged && builder.findField(dragged)) {
    builder.select(dragged)
    emit('added')
  }
  dragged = null
}
</script>

<template>
  <div class="flex h-full min-h-0 flex-col gap-3">
    <UInput
      v-model="query"
      icon="i-lucide-search"
      :placeholder="t('builder.palette.search')"
      size="sm"
      class="w-full"
      :aria-label="t('builder.palette.search')"
    />
    <div class="-me-2 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pe-2">
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
          filter="[data-soon]"
          class="grid grid-cols-1 gap-0.5"
          @start="builder.history.record()"
          @end="onEnd"
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
            <UBadge
              v-if="item.soon"
              :label="t('builder.soon')"
              color="neutral"
              variant="outline"
              size="sm"
              class="ms-auto"
            />
          </UButton>
        </VueDraggable>
      </section>
      <p v-if="!groups.length" class="px-1 text-sm text-muted">{{ t('builder.palette.none') }}</p>
    </div>
  </div>
</template>

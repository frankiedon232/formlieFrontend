<!--
  Click-to-add (owner 2026-10-08): clicking an empty spot of the page opens a searchable field list
  right where you clicked; picking a field puts it there (the canvas works out the row) and the
  list closes. Type to search, ↑ / ↓ and Enter to pick, Esc to close.
-->
<script setup lang="ts">
import { FIELD_CATEGORIES, FIELD_TYPES, type FieldType } from '#shared/utils/forms/fields'

const open = defineModel<boolean>('open', { required: true })
defineProps<{ x: number; y: number }>()
const emit = defineEmits<{ pick: [type: FieldType] }>()
const { t } = useI18n()

const groups = computed(() =>
  FIELD_CATEGORIES.map(category => ({
    id: category,
    label: t(`builder.category.${category}`),
    items: (Object.keys(FIELD_TYPES) as FieldType[])
      .filter(type => FIELD_TYPES[type].category === category && !('soon' in FIELD_TYPES[type]))
      .map(type => ({ id: type, label: t(`builder.field.${type}`), icon: fieldIcon(type), onSelect: () => pick(type) })),
  })).filter(group => group.items.length),
)
function pick(type: FieldType) {
  open.value = false
  emit('pick', type)
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ side: 'bottom', align: 'start', sideOffset: 4, collisionPadding: 12 }">
    <!-- An invisible anchor at the click, so the list opens right there -->
    <span class="pointer-events-none fixed size-px" :style="{ left: `${x}px`, top: `${y}px` }" aria-hidden="true" />
    <template #content>
      <UCommandPalette
        :groups="groups"
        :placeholder="t('builder.palette.search')"
        :fuse="{ resultLimit: 40 }"
        class="h-80 w-72 max-w-[calc(100vw-2rem)]"
        autofocus
        @update:open="value => !value && (open = false)"
      />
    </template>
  </UPopover>
</template>

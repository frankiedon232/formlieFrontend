<!--
  Options editor: reorder (drag or ↑ / ↓), rename, remove, add, paste a list. Matrix fields also
  edit their rows here. Values stay stable when labels change (answers keep matching).
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const builder = useBuilder()
const pasteOpen = ref(false)
const pasteText = ref('')

const options = computed({
  get: () => props.field.options ?? [],
  set: next => builder.updateField(props.field.id, { options: next }, `options:${props.field.id}:order`),
})
const rows = computed<string[]>(() => (props.field.props?.rows as string[] | undefined) ?? [])

const uniqueValue = (label: string, taken: string[]) => {
  const base =
    label
      .toLowerCase()
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || 'option'
  let value = base
  let n = 2
  while (taken.includes(value)) value = `${base}_${n++}`
  return value
}

function setLabel(index: number, label: string) {
  const next = options.value.map((option, i) => (i === index ? { ...option, label } : option))
  builder.updateField(props.field.id, { options: next }, `options:${props.field.id}:${index}`)
}
function add(label = t('builder.defaults.option', { n: options.value.length + 1 })) {
  const value = uniqueValue(
    label,
    options.value.map(o => o.value),
  )
  builder.updateField(props.field.id, { options: [...options.value, { value, label }] })
}
function remove(index: number) {
  builder.updateField(props.field.id, { options: options.value.filter((_, i) => i !== index) })
}
function move(index: number, direction: -1 | 1) {
  const next = [...options.value]
  next.splice(index + direction, 0, ...next.splice(index, 1))
  builder.updateField(props.field.id, { options: next })
}
function applyPaste() {
  const labels = pasteText.value
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .slice(0, 500)
  const taken: string[] = []
  const next = labels.map(label => {
    const value = uniqueValue(label, taken)
    taken.push(value)
    return { value, label }
  })
  if (next.length) builder.updateField(props.field.id, { options: next })
  pasteOpen.value = false
}
watch(pasteOpen, open => {
  if (open) pasteText.value = options.value.map(o => o.label).join('\n')
})

const setRows = (next: string[]) =>
  builder.updateProps(props.field.id, { rows: next }, `rows:${props.field.id}`)
</script>

<template>
  <section class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <h3 class="text-xs font-medium text-muted uppercase">
        {{ field.type === 'matrix' ? t('builder.inspector.columns') : t('builder.inspector.options') }}
      </h3>
      <UButton
        :label="t('builder.inspector.paste')"
        icon="i-lucide-clipboard-paste"
        color="neutral"
        variant="link"
        size="xs"
        class="px-0"
        @click="pasteOpen = true"
      />
    </div>
    <VueDraggable
      v-model="options"
      handle="[data-option-handle]"
      :animation="150"
      class="flex flex-col gap-1.5"
    >
      <div v-for="(option, index) in options" :key="option.value" class="flex items-center gap-1">
        <UIcon
          name="i-lucide-grip-vertical"
          class="size-4 shrink-0 cursor-grab text-muted"
          data-option-handle
          aria-hidden="true"
        />
        <UInput
          :model-value="option.label"
          size="sm"
          class="min-w-0 flex-1"
          :aria-label="t('builder.inspector.optionN', { n: index + 1 })"
          @update:model-value="v => setLabel(index, String(v))"
        />
        <UButton
          icon="i-lucide-arrow-up"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          :disabled="index === 0"
          :aria-label="t('builder.actions.moveUp')"
          @click="move(index, -1)"
        />
        <UButton
          icon="i-lucide-arrow-down"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          :disabled="index === options.length - 1"
          :aria-label="t('builder.actions.moveDown')"
          @click="move(index, 1)"
        />
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          :aria-label="t('builder.inspector.removeOption', { label: option.label })"
          @click="remove(index)"
        />
      </div>
    </VueDraggable>
    <UButton
      :label="t('builder.inspector.addOption')"
      icon="i-lucide-plus"
      color="neutral"
      variant="outline"
      size="sm"
      class="self-start"
      @click="add()"
    />

    <template v-if="field.type === 'matrix'">
      <h3 class="mt-2 text-xs font-medium text-muted uppercase">{{ t('builder.inspector.rows') }}</h3>
      <div v-for="(row, index) in rows" :key="index" class="flex items-center gap-1">
        <UInput
          :model-value="row"
          size="sm"
          class="min-w-0 flex-1"
          :aria-label="t('builder.inspector.rowN', { n: index + 1 })"
          @update:model-value="v => setRows(rows.map((r, i) => (i === index ? String(v) : r)))"
        />
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          :aria-label="t('builder.inspector.removeRow', { n: index + 1 })"
          @click="setRows(rows.filter((_, i) => i !== index))"
        />
      </div>
      <UButton
        :label="t('builder.inspector.addRow')"
        icon="i-lucide-plus"
        color="neutral"
        variant="outline"
        size="sm"
        class="self-start"
        @click="setRows([...rows, t('builder.defaults.row', { n: rows.length + 1 })])"
      />
    </template>

    <AppModal
      v-model:open="pasteOpen"
      :title="t('builder.inspector.pasteTitle')"
      :description="t('builder.inspector.pasteDesc')"
    >
      <template #body>
        <UTextarea v-model="pasteText" :rows="10" autoresize class="w-full" />
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-2">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="pasteOpen = false" />
          <UButton :label="t('builder.inspector.pasteApply')" color="neutral" @click="applyPaste" />
        </div>
      </template>
    </AppModal>
  </section>
</template>

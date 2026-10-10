<!--
  Options editor: reorder (drag or ↑ / ↓), rename, remove, add, paste a list. Matrix fields also
  edit their rows here. Values stay stable when labels change (answers keep matching).
-->
<script setup lang="ts">
import { LONG_FROM, matchesList, offeredOptions } from '#shared/utils/forms/options'
import { VueDraggable } from 'vue-draggable-plus'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField }>()
const { t } = useI18n()
const { number } = useFormat()
const builder = useBuilder()
const pasteOpen = ref(false)
const pasteText = ref('')

const options = computed({
  get: () => props.field.options ?? [],
  set: next => builder.updateField(props.field.id, { options: next }, `options:${props.field.id}:order`),
})

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

// Numbers per option, for calculations (a choice counts as its option's number).
const numbered = computed(() => options.value.some(o => typeof o.score === 'number'))
function setNumbered(on: boolean) {
  builder.updateField(props.field.id, {
    options: options.value.map(({ score: _score, ...o }, i) => (on ? { ...o, score: i + 1 } : o)),
  })
}
function setScore(index: number, raw: string | number) {
  const score = raw === '' || Number.isNaN(Number(raw)) ? 0 : Number(raw)
  builder.updateField(
    props.field.id,
    { options: options.value.map((o, i) => (i === index ? { ...o, score } : o)) },
    `options:${props.field.id}:score:${index}`,
  )
}

// Option lists: fill from a saved list, or save these options as one.
const library = useFieldLibrary()
onMounted(() => library.load())
const listItems = computed(() => library.lists.value.map(l => ({ value: l.id, label: l.name, icon: 'i-lucide-list' })))
function useList(id: string) {
  const list = library.lists.value.find(l => l.id === id)
  if (list) builder.updateField(props.field.id, { options: offeredOptions(toRaw(list)), option_set_id: list.id })
}
// The list this field came from (F15): say when it changed since, with one click to take it over
const linked = computed(() => (props.field.option_set_id ? (library.lists.value.find(l => l.id === props.field.option_set_id) ?? null) : null))
const listChanged = computed(() => !!linked.value && !matchesList(props.field.options, linked.value))
// A long list's options are edited in List Option; here a summary, not hundreds of rows (F15 M3)
const long = computed(() => !!props.field.option_set_id && options.value.length > LONG_FROM)
const saveListOpen = ref(false)

</script>

<template>
  <section class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <h3 class="text-xs font-medium text-muted uppercase">
        {{ field.type === 'matrix' ? t('builder.inspector.columns') : t('builder.inspector.options') }}
      </h3>
      <UButton
        v-if="!long"
        :label="t('builder.inspector.paste')"
        icon="i-lucide-clipboard-paste"
        color="neutral"
        variant="link"
        size="xs"
        class="px-0"
        @click="pasteOpen = true"
      />
    </div>
    <UAlert v-if="listChanged && linked" color="warning" variant="subtle" icon="i-lucide-refresh-ccw" :title="t('library.listChanged', { name: linked.name })" :actions="[{ label: t('library.updateFromList'), color: 'neutral', variant: 'outline', size: 'xs', onClick: () => useList(linked!.id) }]" :ui="{ title: 'text-xs' }" />
    <div v-if="field.type !== 'matrix'" class="flex items-center gap-2">
      <USelectMenu
        :model-value="undefined"
        :items="listItems"
        value-key="value"
        :loading="library.loading.value"
        :placeholder="t('library.useList')"
        icon="i-lucide-list"
        size="sm"
        :search-input="{ placeholder: t('common.search') }"
        class="min-w-0 flex-1"
        @update:model-value="v => v && useList(String(v))"
      />
      <UButton
        v-if="useCan().can('lists.create')"
        :label="t('library.saveAsList')"
        icon="i-lucide-list-plus"
        color="neutral"
        variant="outline"
        size="sm"
        :disabled="!options.length"
        @click="saveListOpen = true"
      />
    </div>
    <div v-if="long" class="flex flex-col gap-2 rounded-lg border border-default p-3">
      <p class="text-sm text-highlighted">{{ t('builder.inspector.longList', { n: number(options.length), name: linked?.name ?? '' }) }}</p>
      <div class="flex flex-wrap gap-1">
        <UBadge v-for="option in options.slice(0, 6)" :key="option.value" :label="option.label" color="neutral" variant="outline" size="sm" class="max-w-32 truncate" />
        <UBadge :label="`+${number(options.length - 6)}`" color="neutral" variant="soft" size="sm" />
      </div>
      <UButton :label="t('builder.level.editList')" icon="i-lucide-external-link" color="neutral" variant="link" size="xs" class="w-fit px-0" :to="`/option-sets/${field.option_set_id}`" target="_blank" />
    </div>
    <VueDraggable
      v-else
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
        <UInput
          v-if="numbered"
          type="number"
          :model-value="String(option.score ?? 0)"
          size="sm"
          class="w-16 shrink-0"
          :aria-label="t('builder.inspector.optionScore', { label: option.label })"
          @update:model-value="v => setScore(index, v)"
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
      v-if="!long"
      :label="t('builder.inspector.addOption')"
      icon="i-lucide-plus"
      color="neutral"
      variant="outline"
      size="sm"
      class="self-start"
      @click="add()"
    />
    <USwitch
      v-if="field.type !== 'ranking'"
      :model-value="numbered"
      :label="t('builder.inspector.numbered')"
      :description="t('builder.inspector.numberedHint')"
      color="neutral"
      size="sm"
      @update:model-value="setNumbered"
    />

    <FormsBuilderInspectorMatrixRows v-if="field.type === 'matrix'" :field="field" />

    <FormsBuilderListModal
      v-model:open="saveListOpen"
      :list="null"
      :initial-name="field.label"
      :initial-options="options"
      @saved="list => builder.updateField(field.id, { option_set_id: list.id })"
    />

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

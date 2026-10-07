<!--
  Option list editor → Levels (F15 M2): a plain list has one level; a list with levels (Country → Region
  → City, Product → Category → Type → Brand) names up to five. Each option below the top sits under one
  option on the level above, and in a form each level opens with only what is under the choice above.
  Removing a level removes its options (asked first when some were saved).
-->
<script setup lang="ts">
import type { OptionItem, OptionLevel } from '#shared/types/forms'
import { uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

const levels = defineModel<OptionLevel[] | null>('levels', { required: true })
const options = defineModel<OptionItem[]>('options', { required: true })
const props = defineProps<{ savedValues: Set<string> }>()
const { t } = useI18n()
const { number } = useFormat()
const confirm = useConfirm()

const MAX = 5
const countAt = (level: number) => options.value.filter(option => (option.level ?? 0) === level).length
const keyFor = (label: string) => uniqueValue(valueFromLabel(label) || 'level', (levels.value ?? []).map(item => item.key))

/** Two levels to start with: the options there now stay on top. */
function start() {
  levels.value = [{ key: 'level_1', label: t('optionSets.levels.nameN', { n: 1 }) }, { key: 'level_2', label: t('optionSets.levels.nameN', { n: 2 }) }]
}
function add() {
  if (!levels.value || levels.value.length >= MAX) return
  const label = t('optionSets.levels.nameN', { n: levels.value.length + 1 })
  levels.value = [...levels.value, { key: keyFor(label), label }]
}
function rename(index: number, label: string) {
  if (!levels.value) return
  levels.value = levels.value.map((item, i) => (i === index ? { ...item, label } : item))
}
/** Removes the last level and its options; back to two levels means one, a plain list. */
async function removeLast() {
  if (!levels.value) return
  const last = levels.value.length - 1
  const gone = options.value.filter(option => (option.level ?? 0) === last)
  if (gone.some(option => props.savedValues.has(option.value))) {
    const ok = await confirm({ title: t('optionSets.levels.removeTitle', { name: levels.value[last]!.label }), description: t('optionSets.levels.removeDesc', { n: gone.length }, gone.length), confirmLabel: t('optionSets.levels.remove'), danger: true })
    if (!ok) return
  }
  options.value = options.value.filter(option => (option.level ?? 0) !== last)
  if (last <= 1) {
    levels.value = null
    options.value = options.value.map(({ level: _level, parent: _parent, ...rest }) => rest)
  } else {
    levels.value = levels.value.slice(0, last)
  }
}
</script>

<template>
  <div class="flex flex-col gap-2 rounded-lg border border-default p-3">
    <div class="flex flex-wrap items-center gap-2">
      <UIcon :name="levels ? 'i-lucide-network' : 'i-lucide-list'" class="size-4 shrink-0 text-muted" />
      <div class="flex min-w-0 flex-1 flex-col">
        <span class="text-sm font-medium text-highlighted">{{ levels ? t('optionSets.levels.title', { n: levels.length }) : t('optionSets.levels.plain') }}</span>
        <span class="text-xs text-muted">{{ levels ? t('optionSets.levels.hint') : t('optionSets.levels.plainHint') }}</span>
      </div>
      <UButton v-if="!levels" :label="t('optionSets.levels.start')" icon="i-lucide-network" color="neutral" variant="outline" size="sm" @click="start" />
    </div>
    <ol v-if="levels" class="flex flex-wrap items-center gap-1.5" :aria-label="t('optionSets.levels.chain')">
      <template v-for="(item, index) in levels" :key="index">
        <li class="flex items-center gap-1">
          <UInput :model-value="item.label" size="sm" maxlength="60" class="w-36" :aria-label="t('optionSets.levels.nameOf', { n: index + 1 })" :highlight="!item.label.trim()" :color="!item.label.trim() ? 'error' : undefined" @update:model-value="value => rename(index, String(value))">
            <template #trailing><span class="text-[11px] text-muted tabular-nums">{{ number(countAt(index)) }}</span></template>
          </UInput>
          <UTooltip v-if="index === levels.length - 1" :text="t('optionSets.levels.remove')">
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" :aria-label="t('optionSets.levels.remove')" @click="removeLast" />
          </UTooltip>
        </li>
        <li v-if="index < levels.length - 1" aria-hidden="true"><UIcon name="i-lucide-chevron-right" class="size-4 text-muted rtl:rotate-180" /></li>
      </template>
      <li v-if="levels.length < MAX"><UButton :label="t('optionSets.levels.add')" icon="i-lucide-plus" color="neutral" variant="ghost" size="sm" @click="add" /></li>
    </ol>
  </div>
</template>

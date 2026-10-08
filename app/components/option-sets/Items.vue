<!--
  Option list editor → Options (F15 M1): one row per option with its label (what people see) and, when
  shown, its value (what answers store) and score. Reorder by dragging the handle or with ↑ / ↓; retire an
  option (no longer offered, old answers still read) or remove one added since the last save. New labels
  get a value of their own; repeated values are marked. Long lists show 100 rows at a time and search.
  Lists with levels (F15 M2): one level at a time, each option with the one above it (searchable), a
  filter by the option above, and "N under it" to go down a level filtered to that option.
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import type { OptionItem, OptionLevel } from '#shared/types/forms'
import { repeatedValues, uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

const options = defineModel<OptionItem[]>({ required: true })
const props = defineProps<{ savedValues: Set<string>; levels?: OptionLevel[] | null }>()
const emit = defineEmits<{ paste: []; import: [] }>()
const { t } = useI18n()
const { number } = useFormat()

const showValues = ref(false)
const showScores = ref(options.value.some(option => option.score !== undefined))
const q = ref('')
const limit = ref(100)
// Lists with levels: the level shown and, below the top, the option above to filter by
const level = ref(0)
const under = ref<string | null>(null)
watch(() => props.levels?.length ?? 0, count => count <= level.value && ((level.value = Math.max(0, count - 1)), (under.value = null)))
const levelOf = (option: OptionItem) => option.level ?? 0
const atLevel = (at: number) => options.value.filter(option => levelOf(option) === at)
const parents = computed(() => (props.levels && level.value > 0 ? atLevel(level.value - 1) : []))
const parentItems = computed(() => parents.value.map(option => ({ value: option.value, label: option.label || option.value })))
const childCount = computed(() => {
  const counts = new Map<string, number>()
  for (const option of options.value) if (option.parent && levelOf(option) === level.value + 1) counts.set(option.parent, (counts.get(option.parent) ?? 0) + 1)
  return counts
})
const levelTabs = computed(() => (props.levels ?? []).map((item, i) => ({ value: i, label: item.label || t('optionSets.levels.nameN', { n: i + 1 }), badge: number(atLevel(i).length) })))
const pickLevel = (at: number) => ((level.value = at), (under.value = null), (q.value = ''))
/** Go down a level to what is under this option. */
const openUnder = (option: OptionItem) => ((level.value = levelOf(option) + 1), (under.value = option.value), (q.value = ''))
const orphan = (option: OptionItem) => levelOf(option) > 0 && !parents.value.some(item => item.value === option.parent)
const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  const pool = props.levels ? options.value.filter(option => levelOf(option) === level.value && (!under.value || option.parent === under.value)) : options.value
  return term ? pool.filter(option => `${option.label} ${option.value}`.toLowerCase().includes(term)) : pool
})
const shown = computed(() => filtered.value.slice(0, limit.value))
// Dragging works on the whole plain list only (not while searching or with rows hidden)
const draggable = computed({
  get: () => options.value,
  set: list => (options.value = list),
})
const canDrag = computed(() => !props.levels && !q.value.trim() && options.value.length <= limit.value)
const repeated = computed(() => repeatedValues(options.value.map(option => option.value)))
const active = computed(() => filtered.value.filter(option => option.active !== false).length)

// Rows keep their identity while label and value are typed (the value can change with the label)
const ids = new WeakMap<OptionItem, number>()
let next = 0
const keyOf = (option: OptionItem) => ids.get(option) ?? (ids.set(option, ++next), next)

const uid = useId()
async function add() {
  const value = uniqueValue('option', options.value.map(option => option.value))
  const parent = level.value > 0 ? (under.value ?? parents.value[0]?.value) : undefined
  options.value = [...options.value, { value, label: '', ...(props.levels && level.value > 0 ? { level: level.value, parent } : {}) }]
  q.value = ''
  limit.value = Math.max(limit.value, filtered.value.length)
  await nextTick()
  document.getElementById(`${uid}-${options.value.length - 1}`)?.focus()
}
/** A new option takes its value from its label, until someone sets the value by hand. */
function setLabel(option: OptionItem, label: string) {
  const fresh = !props.savedValues.has(option.value)
  const auto = fresh && (option.value === valueFromLabel(option.label) || /^option(_\d+)?$/.test(option.value))
  option.label = label
  if (auto && label.trim()) option.value = uniqueValue(valueFromLabel(label), options.value.filter(item => item !== option).map(item => item.value))
}
const indexOf = (option: OptionItem) => options.value.indexOf(option)
const placeOf = (option: OptionItem) => filtered.value.indexOf(option)
/** Swaps with the option next to it in what is shown (same level and option above). */
function move(option: OptionItem, step: -1 | 1) {
  const other = filtered.value[placeOf(option) + step]
  if (!other) return
  const list = [...options.value]
  const a = list.indexOf(option)
  const b = list.indexOf(other)
  list[a] = other
  list[b] = option
  options.value = list
}
/** Removes an option added since the last save and, in a list with levels, the unsaved ones under it. */
function remove(option: OptionItem) {
  const gone = new Set([option.value])
  for (let at = levelOf(option) + 1; props.levels && at < props.levels.length; at++) for (const item of atLevel(at)) if (item.parent && gone.has(item.parent) && !props.savedValues.has(item.value)) gone.add(item.value)
  options.value = options.value.filter(item => !gone.has(item.value))
}
const setParent = (option: OptionItem, value: unknown) => typeof value === 'string' && value && (option.parent = value)
const setActive = (option: OptionItem, on: boolean) => (on ? delete option.active : (option.active = false))
const setScore = (option: OptionItem, text: string) => (text.trim() === '' || Number.isNaN(Number(text)) ? delete option.score : (option.score = Number(text)))
</script>

<template>
  <div class="flex flex-col gap-3">
    <div v-if="levels" class="flex flex-wrap items-center gap-2">
      <UTabs :model-value="level" :items="levelTabs" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="w-fit max-w-full overflow-x-auto" @update:model-value="value => pickLevel(Number(value))" />
      <label v-if="level > 0" class="flex w-full items-center gap-2 sm:w-auto">
        <span class="shrink-0 text-xs text-muted">{{ t('optionSets.levels.under') }}</span>
        <USelectMenu :model-value="under ?? undefined" :items="parentItems" value-key="value" :placeholder="t('optionSets.levels.anyAbove', { name: levels[level - 1]?.label ?? '' })" :search-input="{ placeholder: t('optionSets.items.search') }" size="sm" class="min-w-0 flex-1 sm:w-56" clear @update:model-value="value => (under = typeof value === 'string' ? value : null)" />
      </label>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <UInput v-model="q" icon="i-lucide-search" :placeholder="t('optionSets.items.search')" size="sm" class="w-full sm:w-64" />
      <USwitch v-model="showValues" :label="t('optionSets.items.showValues')" size="sm" color="neutral" />
      <USwitch v-model="showScores" :label="t('optionSets.items.showScores')" size="sm" color="neutral" />
      <div class="ms-auto flex flex-wrap gap-2">
        <UButton :label="t('optionSets.items.paste')" icon="i-lucide-clipboard-paste" color="neutral" variant="outline" size="sm" @click="emit('paste')" />
        <UButton :label="t('optionSets.items.import')" icon="i-lucide-file-up" color="neutral" variant="outline" size="sm" @click="emit('import')" />
        <UButton :label="t('optionSets.items.add')" icon="i-lucide-plus" color="neutral" size="sm" :disabled="level > 0 && !parents.length" @click="add" />
      </div>
    </div>
    <p class="text-xs text-muted">{{ t('optionSets.items.summary', { active: number(active), total: number(filtered.length) }) }}<template v-if="repeated.size"> · <span class="text-error">{{ t('optionSets.items.repeated', { n: repeated.size }, repeated.size) }}</span></template></p>

    <AppEmpty v-if="!filtered.length && !q.trim()" size="sm" icon="i-lucide-list-plus" :title="t('optionSets.items.none')" :description="level > 0 && !parents.length ? t('optionSets.levels.aboveFirst', { name: levels?.[level - 1]?.label ?? '' }) : t('optionSets.items.noneDesc')" :actions="level > 0 && !parents.length ? [{ label: levels?.[level - 1]?.label ?? '', icon: 'i-lucide-arrow-left', color: 'neutral', variant: 'outline', onClick: () => pickLevel(level - 1) }] : [{ label: t('optionSets.items.add'), icon: 'i-lucide-plus', color: 'neutral', onClick: add }]" />
    <AppEmpty v-else-if="!filtered.length" size="xs" icon="i-lucide-search-x" :title="t('optionSets.items.noMatch')" />
    <component :is="canDrag ? VueDraggable : 'ul'" v-else v-model="draggable" handle="[data-option-handle]" :animation="150" tag="ul" class="flex flex-col divide-y divide-default rounded-lg border border-default">
      <li v-for="option in shown" :key="keyOf(option)" class="flex items-center gap-2 px-2 py-1.5" :class="option.active === false ? 'bg-elevated/40' : ''">
        <UButton v-if="canDrag" data-option-handle icon="i-lucide-grip-vertical" color="neutral" variant="ghost" size="xs" class="cursor-grab text-muted" :aria-label="t('optionSets.items.drag')" tabindex="-1" />
        <UInput :id="`${uid}-${indexOf(option)}`" :model-value="option.label" :placeholder="t('optionSets.items.labelPlaceholder')" size="sm" class="min-w-0 flex-1" :class="option.active === false ? 'opacity-60' : ''" :aria-label="t('optionSets.items.label')" @update:model-value="value => setLabel(option, String(value))" />
        <USelectMenu v-if="levels && level > 0" :model-value="option.parent" :items="parentItems" value-key="value" :search-input="{ placeholder: t('optionSets.items.search') }" size="sm" class="w-28 sm:w-44" :color="orphan(option) ? 'error' : undefined" :highlight="orphan(option)" :placeholder="t('optionSets.levels.pickAbove')" :aria-label="t('optionSets.levels.above', { name: levels[level - 1]?.label ?? '' })" @update:model-value="value => setParent(option, value)" />
        <UInput v-if="showValues" v-model="option.value" size="sm" class="w-32 font-mono sm:w-44" :color="repeated.has(option.value.toLowerCase()) ? 'error' : undefined" :highlight="repeated.has(option.value.toLowerCase())" :disabled="savedValues.has(option.value)" :aria-label="t('optionSets.items.value')" />
        <UInput v-if="showScores" :model-value="option.score === undefined ? '' : String(option.score)" type="number" size="sm" class="w-20" :aria-label="t('optionSets.items.score')" @update:model-value="value => setScore(option, String(value))" />
        <UButton v-if="levels && level < levels.length - 1" :label="t('optionSets.levels.underIt', { n: number(childCount.get(option.value) ?? 0) })" trailing-icon="i-lucide-chevron-right" color="neutral" variant="soft" size="xs" class="shrink-0" :ui="{ trailingIcon: 'rtl:rotate-180' }" @click="openUnder(option)" />
        <UBadge v-if="option.active === false" :label="t('optionSets.items.retired')" color="neutral" variant="soft" size="sm" class="hidden sm:inline-flex" />
        <div class="flex shrink-0 items-center">
          <UButton icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="xs" :disabled="placeOf(option) === 0 || !!q" :aria-label="t('optionSets.items.up')" @click="move(option, -1)" />
          <UButton icon="i-lucide-arrow-down" color="neutral" variant="ghost" size="xs" :disabled="placeOf(option) === filtered.length - 1 || !!q" :aria-label="t('optionSets.items.down')" @click="move(option, 1)" />
          <UTooltip :text="option.active === false ? t('optionSets.items.bringBack') : t('optionSets.items.retire')">
            <UButton :icon="option.active === false ? 'i-lucide-archive-restore' : 'i-lucide-archive'" color="neutral" variant="ghost" size="xs" :aria-label="option.active === false ? t('optionSets.items.bringBack') : t('optionSets.items.retire')" @click="setActive(option, option.active === false)" />
          </UTooltip>
          <UTooltip :text="savedValues.has(option.value) ? t('optionSets.items.retireInstead') : t('optionSets.items.remove')">
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" :disabled="savedValues.has(option.value)" :aria-label="t('optionSets.items.remove')" @click="remove(option)" />
          </UTooltip>
        </div>
      </li>
    </component>
    <UButton v-if="filtered.length > limit" :label="t('optionSets.items.more', { n: number(filtered.length - limit) })" color="neutral" variant="outline" size="sm" class="self-center" @click="limit += 200" />
  </div>
</template>

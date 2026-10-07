<!--
  Option list editor → Options (F15 M1): one row per option with its label (what people see) and, when
  shown, its value (what answers store) and score. Reorder by dragging the handle or with ↑ / ↓; retire an
  option (no longer offered, old answers still read) or remove one added since the last save. New labels
  get a value of their own; repeated values are marked. Long lists show 100 rows at a time and search.
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import type { OptionItem } from '#shared/types/forms'
import { repeatedValues, uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

const options = defineModel<OptionItem[]>({ required: true })
const props = defineProps<{ savedValues: Set<string> }>()
const emit = defineEmits<{ paste: []; import: [] }>()
const { t } = useI18n()
const { number } = useFormat()

const showValues = ref(false)
const showScores = ref(options.value.some(option => option.score !== undefined))
const q = ref('')
const limit = ref(100)
const filtered = computed(() => {
  const term = q.value.trim().toLowerCase()
  return term ? options.value.filter(option => `${option.label} ${option.value}`.toLowerCase().includes(term)) : options.value
})
const shown = computed(() => filtered.value.slice(0, limit.value))
// Dragging works on the whole list only (not while searching or with rows hidden)
const draggable = computed({
  get: () => options.value,
  set: list => (options.value = list),
})
const canDrag = computed(() => !q.value.trim() && options.value.length <= limit.value)
const repeated = computed(() => repeatedValues(options.value.map(option => option.value)))
const active = computed(() => options.value.filter(option => option.active !== false).length)

// Rows keep their identity while label and value are typed (the value can change with the label)
const ids = new WeakMap<OptionItem, number>()
let next = 0
const keyOf = (option: OptionItem) => ids.get(option) ?? (ids.set(option, ++next), next)

const uid = useId()
async function add() {
  const value = uniqueValue('option', options.value.map(option => option.value))
  options.value = [...options.value, { value, label: '' }]
  q.value = ''
  limit.value = Math.max(limit.value, options.value.length)
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
function move(option: OptionItem, step: -1 | 1) {
  const from = indexOf(option)
  const to = from + step
  if (to < 0 || to >= options.value.length) return
  const list = [...options.value]
  list.splice(to, 0, list.splice(from, 1)[0]!)
  options.value = list
}
const remove = (option: OptionItem) => (options.value = options.value.filter(item => item !== option))
const setActive = (option: OptionItem, on: boolean) => (on ? delete option.active : (option.active = false))
const setScore = (option: OptionItem, text: string) => (text.trim() === '' || Number.isNaN(Number(text)) ? delete option.score : (option.score = Number(text)))
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex flex-wrap items-center gap-2">
      <UInput v-model="q" icon="i-lucide-search" :placeholder="t('optionSets.items.search')" size="sm" class="w-full sm:w-64" />
      <USwitch v-model="showValues" :label="t('optionSets.items.showValues')" size="sm" color="neutral" />
      <USwitch v-model="showScores" :label="t('optionSets.items.showScores')" size="sm" color="neutral" />
      <div class="ms-auto flex flex-wrap gap-2">
        <UButton :label="t('optionSets.items.paste')" icon="i-lucide-clipboard-paste" color="neutral" variant="outline" size="sm" @click="emit('paste')" />
        <UButton :label="t('optionSets.items.import')" icon="i-lucide-file-up" color="neutral" variant="outline" size="sm" @click="emit('import')" />
        <UButton :label="t('optionSets.items.add')" icon="i-lucide-plus" color="neutral" size="sm" @click="add" />
      </div>
    </div>
    <p class="text-xs text-muted">{{ t('optionSets.items.summary', { active: number(active), total: number(options.length) }) }}<template v-if="repeated.size"> · <span class="text-error">{{ t('optionSets.items.repeated', { n: repeated.size }, repeated.size) }}</span></template></p>

    <AppEmpty v-if="!options.length" size="sm" icon="i-lucide-list-plus" :title="t('optionSets.items.none')" :description="t('optionSets.items.noneDesc')" :actions="[{ label: t('optionSets.items.add'), icon: 'i-lucide-plus', color: 'neutral', onClick: add }]" />
    <AppEmpty v-else-if="!filtered.length" size="xs" icon="i-lucide-search-x" :title="t('optionSets.items.noMatch')" />
    <component :is="canDrag ? VueDraggable : 'ul'" v-else v-model="draggable" handle="[data-option-handle]" :animation="150" tag="ul" class="flex flex-col divide-y divide-default rounded-lg border border-default">
      <li v-for="option in shown" :key="keyOf(option)" class="flex items-center gap-2 px-2 py-1.5" :class="option.active === false ? 'bg-elevated/40' : ''">
        <UButton v-if="canDrag" data-option-handle icon="i-lucide-grip-vertical" color="neutral" variant="ghost" size="xs" class="cursor-grab text-muted" :aria-label="t('optionSets.items.drag')" tabindex="-1" />
        <UInput :id="`${uid}-${indexOf(option)}`" :model-value="option.label" :placeholder="t('optionSets.items.labelPlaceholder')" size="sm" class="min-w-0 flex-1" :class="option.active === false ? 'opacity-60' : ''" :aria-label="t('optionSets.items.label')" @update:model-value="value => setLabel(option, String(value))" />
        <UInput v-if="showValues" v-model="option.value" size="sm" class="w-32 font-mono sm:w-44" :color="repeated.has(option.value.toLowerCase()) ? 'error' : undefined" :highlight="repeated.has(option.value.toLowerCase())" :disabled="savedValues.has(option.value)" :aria-label="t('optionSets.items.value')" />
        <UInput v-if="showScores" :model-value="option.score === undefined ? '' : String(option.score)" type="number" size="sm" class="w-20" :aria-label="t('optionSets.items.score')" @update:model-value="value => setScore(option, String(value))" />
        <UBadge v-if="option.active === false" :label="t('optionSets.items.retired')" color="neutral" variant="soft" size="sm" class="hidden sm:inline-flex" />
        <div class="flex shrink-0 items-center">
          <UButton icon="i-lucide-arrow-up" color="neutral" variant="ghost" size="xs" :disabled="indexOf(option) === 0 || !!q" :aria-label="t('optionSets.items.up')" @click="move(option, -1)" />
          <UButton icon="i-lucide-arrow-down" color="neutral" variant="ghost" size="xs" :disabled="indexOf(option) === options.length - 1 || !!q" :aria-label="t('optionSets.items.down')" @click="move(option, 1)" />
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

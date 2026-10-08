<!--
  Option list editor → Paste or Import (F15): options from pasted text or a CSV / Excel file. First the
  shape of a row (owner 2026-10-08, a 3-column file read as one column was the problem):
  - One option per row: columns are label, value, score or a language (guessed from the header).
  - A path per row (Country, Region, City): one column per level. Picked by itself for a list with
    levels, or when the file looks like levels; for a simple list, Apply also creates the levels, named
    from the column headers (up to four).
  A preview says what will be added; "Add and update" keeps the rest, "Replace" retires what the file
  no longer has. Nothing changes until Apply, and the list still needs Save.
-->
<script setup lang="ts">
import type { OptionItem, OptionLevel } from '#shared/types/forms'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { MAX_LIST_LEVELS, uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

const props = defineProps<{ source: 'paste' | 'file'; options: OptionItem[]; languages: string[]; levels?: OptionLevel[] | null }>()
const open = defineModel<boolean>('open', { required: true })
const emit = defineEmits<{ apply: [options: OptionItem[], levels: OptionLevel[] | null] }>()
const { t } = useI18n()
const { number } = useFormat()

const text = ref('')
const file = ref<File | null>(null)
const rows = ref<string[][]>([])
const failed = ref<string | null>(null)
const header = ref(false)
const mode = ref<'merge' | 'replace'>('merge')
watch(open, value => value && ((text.value = ''), (file.value = null), (rows.value = []), (failed.value = null), (mode.value = 'merge'), (header.value = props.source === 'file')))
// Pasted text: the first row counts as column names when it looks like them (files: on by default)
watch(text, value => {
  rows.value = value.trim() ? parseCsv(value) : []
  header.value = looksLikeHeader(rows.value)
})
watch(file, async value => {
  failed.value = null
  rows.value = []
  if (!value) return
  try {
    rows.value = await readTable(value)
  } catch (error) {
    failed.value = (error as Error).message === 'unsupported' ? t('optionSets.import.unsupported') : t('optionSets.import.unreadable')
  }
})
const body = computed(() => (header.value ? rows.value.slice(1) : rows.value))
const width = computed(() => Math.max(0, ...rows.value.map(row => row.length)))
const columnName = (i: number) => (header.value && rows.value[0]?.[i]?.trim()) || t('optionSets.import.column', { n: i + 1 })

// What a row is: one option, or a path through the levels
const shape = ref<'one' | 'path'>('one')
const detected = computed(() => !props.levels && looksLikeLevels(body.value))
watch([rows, header], () => (shape.value = props.levels || detected.value ? 'path' : 'one'), { immediate: true })
const shapes = computed(() => [
  { value: 'one', label: t('optionSets.import.shape.one'), icon: 'i-lucide-list' },
  { value: 'path', label: t('optionSets.import.shape.path'), icon: 'i-lucide-network' },
])

// Columns and what each one is
type Role = 'label' | 'value' | 'score' | 'skip' | `lang:${string}` | `lvl:${number}`
const roles = ref<Role[]>([])
const languageName = (code: string) => APP_LOCALES.find(item => item.code === code)?.name ?? code
function guessOne(name: string, index: number): Role {
  const n = name.trim().toLowerCase()
  if (['value', 'code', 'id', 'key'].includes(n)) return 'value'
  if (['score', 'points', 'weight'].includes(n)) return 'score'
  const lang = props.languages.find(code => n === code.toLowerCase() || n === languageName(code).toLowerCase() || n === APP_LOCALES.find(item => item.code === code)?.englishName.toLowerCase())
  if (lang) return `lang:${lang}`
  return index === 0 ? 'label' : 'skip'
}
function guessPath(name: string, index: number): Role {
  const n = name.trim().toLowerCase()
  const at = (props.levels ?? []).findIndex(level => level.label.toLowerCase() === n || level.key.toLowerCase() === n)
  return at >= 0 ? `lvl:${at}` : index < MAX_LIST_LEVELS ? `lvl:${index}` : 'skip'
}
watch([rows, header, shape], () => (roles.value = Array.from({ length: width.value }, (_, i) => (shape.value === 'path' ? guessPath(header.value ? (rows.value[0]?.[i] ?? '') : '', i) : guessOne(header.value ? (rows.value[0]?.[i] ?? '') : '', i)))), { immediate: true })

/** Levels after applying: the list's own, then new ones named from their column (header) for columns beyond them. */
const columnOf = (level: number) => roles.value.indexOf(`lvl:${level}`)
const usedLevels = computed(() => {
  let count = 0
  while (count < MAX_LIST_LEVELS && columnOf(count) >= 0) count++
  return count
})
const plannedLevels = computed<OptionLevel[]>(() => {
  const own = props.levels ?? []
  const out: OptionLevel[] = []
  for (let i = 0; i < Math.max(own.length, usedLevels.value); i++) {
    if (own[i]) out.push(own[i]!)
    else {
      const label = header.value ? columnName(columnOf(i)) : t('optionSets.levels.nameN', { n: i + 1 })
      out.push({ key: uniqueValue(valueFromLabel(label) || 'level', out.map(item => item.key)), label })
    }
  }
  return out
})
const roleItems = computed(() =>
  shape.value === 'path'
    ? [
        ...Array.from({ length: MAX_LIST_LEVELS }, (_, i) => ({ value: `lvl:${i}`, label: props.levels?.[i]?.label ?? t('optionSets.import.role.level', { n: i + 1 }) })),
        { value: 'skip', label: t('optionSets.import.role.skip') },
      ]
    : [
        { value: 'label', label: t('optionSets.import.role.label') },
        { value: 'value', label: t('optionSets.import.role.value') },
        { value: 'score', label: t('optionSets.import.role.score') },
        ...props.languages.map(code => ({ value: `lang:${code}`, label: t('optionSets.import.role.lang', { name: languageName(code) }) })),
        { value: 'skip', label: t('optionSets.import.role.skip') },
      ],
)

// What applying would do
const replace = computed(() => mode.value === 'replace')
const paths = computed(() => (shape.value === 'path' ? importPaths(props.options, body.value, Array.from({ length: usedLevels.value }, (_, i) => columnOf(i)), replace.value) : null))
const result = computed(() =>
  importRows(props.options, body.value, { label: roles.value.indexOf('label'), value: roles.value.indexOf('value'), score: roles.value.indexOf('score'), languages: roles.value.flatMap((role, i) => (role.startsWith('lang:') ? [[role.slice(5), i] as [string, number]] : [])) }, replace.value),
)
const needsMore = computed(() => (shape.value === 'path' ? usedLevels.value < 2 && !props.levels : !roles.value.includes('label')))
const canApply = computed(() => !needsMore.value && (paths.value ? paths.value.added > 0 || paths.value.retired > 0 : result.value.added > 0 || result.value.updated > 0))
function apply() {
  if (!canApply.value) return
  if (paths.value) emit('apply', paths.value.list, plannedLevels.value.length > 1 ? plannedLevels.value : null)
  else emit('apply', result.value.list, props.levels ?? null)
  open.value = false
}
const modes = computed(() => [
  { value: 'merge', label: t('optionSets.import.merge') },
  { value: 'replace', label: t('optionSets.import.replace') },
])
// A small example of the shape chosen
const example = computed(() => (shape.value === 'path' ? [['Canada', 'Ontario', 'Toronto'], ['Canada', 'Quebec', 'Montréal'], ['Japan', 'Tokyo', 'Shibuya']] : [['North'], ['South'], ['East']]))
</script>

<template>
  <AppModal v-model:open="open" :title="source === 'paste' ? t('optionSets.import.pasteTitle') : t('optionSets.import.fileTitle')" :description="t('optionSets.import.intro')" keep-open :ui="{ content: 'sm:max-w-3xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-2">
          <span class="text-xs font-medium text-highlighted">{{ t('optionSets.import.shape.title') }}</span>
          <UTabs v-model="shape" :items="shapes" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="w-fit max-w-full" />
          <div class="flex flex-col gap-2 rounded-lg border border-default bg-elevated/30 p-3 sm:flex-row sm:items-start sm:gap-4">
            <p class="min-w-0 flex-1 text-xs text-muted">{{ shape === 'path' ? t('optionSets.import.shape.pathHint', { n: MAX_LIST_LEVELS }) : t('optionSets.import.shape.oneHint') }}</p>
            <table class="shrink-0 font-mono text-[11px] text-default" :aria-label="t('optionSets.import.example')">
              <tbody>
                <tr v-for="(line, r) in example" :key="r">
                  <td v-for="(value, c) in line" :key="c" class="border border-default px-1.5 py-0.5">{{ value }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <UAlert v-if="detected && shape === 'path'" color="neutral" variant="subtle" icon="i-lucide-network" :description="t('optionSets.import.detected')" :ui="{ description: 'text-xs' }" />
        </div>

        <UTextarea v-if="source === 'paste'" v-model="text" :rows="6" autoresize :maxrows="12" :placeholder="shape === 'path' ? t('optionSets.import.pastePathPlaceholder') : t('optionSets.import.pastePlaceholder')" class="w-full" autofocus />
        <UFileUpload v-else v-model="file" accept=".csv,.txt,.xlsx,text/csv,text/plain" :label="t('optionSets.import.drop')" :description="t('optionSets.import.types')" icon="i-lucide-file-up" color="neutral" layout="list" class="w-full" />
        <UAlert v-if="failed" color="error" variant="subtle" icon="i-lucide-file-x" :description="failed" />

        <template v-if="rows.length">
          <div class="flex flex-wrap items-center gap-4">
            <UCheckbox v-model="header" :label="t('optionSets.import.header')" color="neutral" />
            <UTabs v-model="mode" :items="modes" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" class="w-fit" />
          </div>
          <div class="overflow-x-auto rounded-lg border border-default">
            <table class="w-full min-w-max text-start text-xs">
              <thead class="bg-elevated/50">
                <tr>
                  <th v-for="(_, i) in width" :key="i" class="px-2 py-2 text-start font-medium">
                    <span class="mb-1 block truncate text-muted">{{ columnName(i) }}</span>
                    <USelect v-model="roles[i]" :items="roleItems" size="xs" class="w-40" :aria-label="columnName(i)" />
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-default">
                <tr v-for="(row, r) in body.slice(0, 6)" :key="r">
                  <td v-for="(_, i) in width" :key="i" class="max-w-48 truncate px-2 py-1.5" :class="roles[i] === 'skip' ? 'text-dimmed' : 'text-default'">{{ row[i] ?? '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="paths && plannedLevels.length > 1" class="flex flex-wrap items-center gap-1 text-xs text-default">
            <UIcon name="i-lucide-network" class="size-3.5 text-muted" />{{ (levels ? t('optionSets.import.levelsKept') : t('optionSets.import.levelsMade')) }}
            <span class="font-medium text-highlighted">{{ plannedLevels.map(level => level.label).join(' → ') }}</span>
          </p>
          <UAlert v-if="paths && !levels && options.length && mode === 'merge'" color="warning" variant="subtle" icon="i-lucide-triangle-alert" :description="t('optionSets.import.existingTop', { n: number(options.length), name: plannedLevels[0]?.label ?? '' }, options.length)" :ui="{ description: 'text-xs' }" />
          <p v-if="paths" class="text-xs text-muted">{{ t('optionSets.import.pathsSummary', { rows: number(body.length), added: number(paths.added), kept: number(paths.kept) }) }}<template v-if="paths.skipped"> · {{ t('optionSets.import.skipped', { n: number(paths.skipped) }) }}</template><template v-if="paths.retired"> · <span class="text-warning">{{ t('optionSets.import.retired', { n: number(paths.retired) }) }}</span></template></p>
          <p v-else class="text-xs text-muted">{{ t('optionSets.import.summary', { rows: number(body.length), added: number(result.added), updated: number(result.updated) }) }}<template v-if="result.skipped"> · {{ t('optionSets.import.skipped', { n: number(result.skipped) }) }}</template><template v-if="result.retired"> · <span class="text-warning">{{ t('optionSets.import.retired', { n: number(result.retired) }) }}</span></template></p>
          <p v-if="needsMore" class="text-xs text-error">{{ shape === 'path' ? t('optionSets.import.needTwoLevels') : t('optionSets.import.needLabel') }}</p>
        </template>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="t('optionSets.import.apply')" icon="i-lucide-check" color="neutral" :disabled="!canApply" @click="apply" />
      </div>
    </template>
  </AppModal>
</template>

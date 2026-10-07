<!--
  Option list editor → Paste or Import (F15 M1): options from pasted text or a CSV / Excel file. Each
  column is mapped to label, value, score or a language (guessed from the header); a preview says what
  will be added and updated. "Add and update" keeps the rest; "Replace" makes the list match the file
  (options missing from it are retired, never deleted, so old answers keep reading). Nothing changes
  until Apply, and the list still needs Save.
-->
<script setup lang="ts">
import type { OptionItem } from '#shared/types/forms'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { uniqueValue, valueFromLabel } from '#shared/utils/forms/options'

const props = defineProps<{ source: 'paste' | 'file'; options: OptionItem[]; languages: string[] }>()
const open = defineModel<boolean>('open', { required: true })
const emit = defineEmits<{ apply: [options: OptionItem[]] }>()
const { t } = useI18n()
const { number } = useFormat()

const text = ref('')
const file = ref<File | null>(null)
const rows = ref<string[][]>([])
const failed = ref<string | null>(null)
const header = ref(false)
const mode = ref<'merge' | 'replace'>('merge')
watch(open, value => value && ((text.value = ''), (file.value = null), (rows.value = []), (failed.value = null), (mode.value = 'merge'), (header.value = props.source === 'file')))
watch(text, value => (rows.value = value.trim() ? parseCsv(value) : []))
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

// Columns and what each one is
type Role = 'label' | 'value' | 'score' | 'skip' | `lang:${string}`
const width = computed(() => Math.max(0, ...rows.value.map(row => row.length)))
const roles = ref<Role[]>([])
const languageName = (code: string) => APP_LOCALES.find(item => item.code === code)?.name ?? code
function guess(name: string, index: number): Role {
  const n = name.trim().toLowerCase()
  if (['value', 'code', 'id', 'key'].includes(n)) return 'value'
  if (['score', 'points', 'weight'].includes(n)) return 'score'
  const lang = props.languages.find(code => n === code.toLowerCase() || n === languageName(code).toLowerCase() || n === APP_LOCALES.find(item => item.code === code)?.englishName.toLowerCase())
  if (lang) return `lang:${lang}`
  return index === 0 ? 'label' : 'skip'
}
watch([rows, header], () => (roles.value = Array.from({ length: width.value }, (_, i) => (header.value ? guess(rows.value[0]?.[i] ?? '', i) : i === 0 ? 'label' : 'skip'))), { immediate: true })
const roleItems = computed(() => [
  { value: 'label', label: t('optionSets.import.role.label') },
  { value: 'value', label: t('optionSets.import.role.value') },
  { value: 'score', label: t('optionSets.import.role.score') },
  ...props.languages.map(code => ({ value: `lang:${code}`, label: t('optionSets.import.role.lang', { name: languageName(code) }) })),
  { value: 'skip', label: t('optionSets.import.role.skip') },
])
const columnName = (i: number) => (header.value ? rows.value[0]?.[i] || t('optionSets.import.column', { n: i + 1 }) : t('optionSets.import.column', { n: i + 1 }))
const body = computed(() => (header.value ? rows.value.slice(1) : rows.value))

// What applying would do
const result = computed(() => {
  const labelAt = roles.value.indexOf('label')
  const valueAt = roles.value.indexOf('value')
  const scoreAt = roles.value.indexOf('score')
  const langs = roles.value.flatMap((role, i) => (role.startsWith('lang:') ? [[role.slice(5), i] as const] : []))
  const list = mode.value === 'replace' ? props.options.map(option => ({ ...option, active: false as boolean | undefined })) : props.options.map(option => ({ ...option }))
  let added = 0
  let updated = 0
  let skipped = 0
  const seen = new Set<OptionItem>()
  for (const row of body.value) {
    const label = labelAt >= 0 ? (row[labelAt] ?? '').trim() : ''
    if (!label) {
      skipped++
      continue
    }
    const wanted = valueAt >= 0 ? (row[valueAt] ?? '').trim() : ''
    const match = list.find(option => (wanted ? option.value.toLowerCase() === wanted.toLowerCase() : option.label.toLowerCase() === label.toLowerCase()))
    const score = scoreAt >= 0 && row[scoreAt]?.trim() && !Number.isNaN(Number(row[scoreAt])) ? Number(row[scoreAt]) : undefined
    const translations = Object.fromEntries(langs.map(([code, i]) => [code, (row[i] ?? '').trim()]).filter(([, value]) => value))
    if (match) {
      if (seen.has(match)) {
        skipped++
        continue
      }
      seen.add(match)
      Object.assign(match, { label, ...(score !== undefined ? { score } : {}), ...(Object.keys(translations).length ? { translations: { ...match.translations, ...translations } } : {}) })
      delete match.active
      updated++
    } else {
      const option: OptionItem = { value: uniqueValue(wanted || valueFromLabel(label), list.map(item => item.value)), label, ...(score !== undefined ? { score } : {}), ...(Object.keys(translations).length ? { translations } : {}) }
      list.push(option)
      seen.add(option)
      added++
    }
  }
  const retired = mode.value === 'replace' ? list.filter(option => option.active === false && props.options.find(item => item.value === option.value)?.active !== false).length : 0
  // Retired ones keep their place but clean (no "active: undefined")
  for (const option of list) if (option.active !== false) delete option.active
  return { list, added, updated, skipped, retired }
})
const canApply = computed(() => roles.value.includes('label') && (result.value.added > 0 || result.value.updated > 0))
function apply() {
  if (!canApply.value) return
  emit('apply', result.value.list)
  open.value = false
}
const modes = computed(() => [
  { value: 'merge', label: t('optionSets.import.merge') },
  { value: 'replace', label: t('optionSets.import.replace') },
])
</script>

<template>
  <AppModal v-model:open="open" :title="source === 'paste' ? t('optionSets.import.pasteTitle') : t('optionSets.import.fileTitle')" :description="source === 'paste' ? t('optionSets.import.pasteDesc') : t('optionSets.import.fileDesc')" keep-open :ui="{ content: 'sm:max-w-3xl' }">
    <template #body>
      <div class="flex flex-col gap-4">
        <UTextarea v-if="source === 'paste'" v-model="text" :rows="6" autoresize :maxrows="12" :placeholder="t('optionSets.import.pastePlaceholder')" class="w-full" autofocus />
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
          <p class="text-xs text-muted">{{ t('optionSets.import.summary', { rows: number(body.length), added: number(result.added), updated: number(result.updated) }) }}<template v-if="result.skipped"> · {{ t('optionSets.import.skipped', { n: number(result.skipped) }) }}</template><template v-if="result.retired"> · <span class="text-warning">{{ t('optionSets.import.retired', { n: number(result.retired) }) }}</span></template></p>
          <p v-if="!roles.includes('label')" class="text-xs text-error">{{ t('optionSets.import.needLabel') }}</p>
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

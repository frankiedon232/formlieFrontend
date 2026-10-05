<!--
  Step 3: the columns. A new table: one column per answer after the response facts; rename a
  column or leave an answer out. A table of theirs: pick what goes in each column (an answer, a
  fact about the response, or nothing); required columns must get something, and a place for the
  response id is needed (Formalie can add one). Problems and warnings show above the list.
-->
<script setup lang="ts">
import type { ColumnSource, MetaColumn, StorageField  } from '#shared/types/destinations'
import { META_COLUMNS } from '#shared/types/destinations'
import { blocking } from '#shared/utils/datasources/tables'

const props = defineProps<{ setup: ReturnType<typeof useStorageSetup>; fields: StorageField[]; editing: boolean }>()
const { t } = useI18n()
const s = props.setup
const byKey = computed(() => new Map(props.fields.map(field => [field.key, field])))
const sourceLabel = (source: ColumnSource | null) => (!source ? t('destinations.columns.nothing') : source.kind === 'meta' ? t(`destinations.meta.${source.key}`) : (byKey.value.get(source.key)?.label ?? source.key))
const sourceIcon = (source: ColumnSource | null) => (!source ? 'i-lucide-circle-dashed' : source.kind === 'meta' ? 'i-lucide-info' : 'i-lucide-text-cursor-input')
const keyOf = (source: ColumnSource | null) => (source ? `${source.kind}:${source.key}` : '')

const choices = computed(() => [
  { value: '', label: t('destinations.columns.nothing') },
  ...META_COLUMNS.map(key => ({ value: `meta:${key}`, label: t(`destinations.meta.${key}`), icon: 'i-lucide-info' })),
  ...props.fields.map(field => ({ value: `field:${field.key}`, label: field.label, icon: 'i-lucide-text-cursor-input' })),
])
function setSource(index: number, value: string) {
  if (!s.manual.value) return
  const [kind, ...rest] = value.split(':')
  const source: ColumnSource | null = !value ? null : kind === 'meta' ? { kind: 'meta', key: rest.join(':') as MetaColumn } : { kind: 'field', key: rest.join(':') }
  s.manual.value = s.manual.value.map((column, i) => (i === index ? { ...column, source } : column))
}
function rename(key: string, value: string) {
  s.renames.value = { ...s.renames.value, [key]: value.trim() }
}
const toggleSkip = (key: string, store: boolean) => (s.skipped.value = store ? s.skipped.value.filter(item => item !== key) : [...s.skipped.value, key])
const manualMode = computed(() => s.mode.value === 'existing' || props.editing)
const problems = computed(() => blocking(s.issues.value))
const warnings = computed(() => s.issues.value.filter(issue => issue.code === 'type_mismatch'))
const columnIssue = (column: string) => s.issues.value.find(issue => issue.column === column)
const issueText = (issue: ReturnType<typeof useStorageSetup>['issues']['value'][number]) => t(`destinations.issue.${issue.code}`, { column: issue.column ?? '', field: 'field' in issue ? (byKey.value.get(issue.field)?.label ?? issue.field) : '' })
</script>

<template>
  <div class="flex flex-col gap-4">
    <UAlert v-if="problems.length" icon="i-lucide-circle-x" color="error" variant="subtle" :title="t('destinations.columns.problems')">
      <template #description>
        <ul class="mt-1 flex flex-col gap-1">
          <li v-for="issue in problems" :key="`${issue.code}${issue.column}`">{{ issueText(issue) }}</li>
        </ul>
        <UButton v-if="problems.some(issue => issue.code === 'no_key') && manualMode && s.fullAccess.value" :label="t('destinations.columns.addKey')" icon="i-lucide-plus" color="neutral" variant="outline" size="xs" class="mt-2" @click="s.addKeyColumn()" />
      </template>
    </UAlert>
    <UAlert v-if="warnings.length" icon="i-lucide-triangle-alert" color="warning" variant="subtle" :title="t('destinations.columns.warnings')">
      <template #description>
        <ul class="mt-1 flex flex-col gap-1">
          <li v-for="issue in warnings" :key="`${issue.code}${issue.column}`">{{ issueText(issue) }}</li>
        </ul>
      </template>
    </UAlert>

    <div class="overflow-hidden rounded-lg border border-default">
      <div class="hidden grid-cols-[minmax(0,1fr)_minmax(0,1fr)_8rem] gap-3 border-b border-default bg-elevated/50 px-3 py-2 text-xs font-medium text-muted sm:grid">
        <span>{{ manualMode ? t('destinations.columns.column') : t('destinations.columns.answer') }}</span>
        <span>{{ manualMode ? t('destinations.columns.fills') : t('destinations.columns.column') }}</span>
        <span>{{ t('destinations.columns.type') }}</span>
      </div>
      <ul class="divide-y divide-default">
        <!-- A table of theirs (or editing): pick what fills each column -->
        <template v-if="manualMode">
          <li v-for="(column, index) in s.manual.value ?? []" :key="column.column" class="grid grid-cols-1 items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_8rem] sm:gap-3" :class="columnIssue(column.column) ? 'bg-error/5' : ''">
            <span class="flex min-w-0 items-center gap-1.5">
              <code class="truncate font-mono text-xs text-highlighted" dir="ltr">{{ column.column }}</code>
              <span v-if="!column.nullable" class="text-error" :title="t('destinations.columns.required')">*</span>
              <UBadge v-if="!column.existing" :label="t('destinations.columns.new')" color="neutral" variant="outline" size="sm" class="rounded-md" />
            </span>
            <USelectMenu :model-value="keyOf(column.source)" :items="choices" value-key="value" size="sm" class="w-full" :aria-label="t('destinations.columns.fillsFor', { column: column.column })" @update:model-value="value => setSource(index, String(value ?? ''))" />
            <code class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ column.type }}</code>
          </li>
        </template>
        <!-- A new table: one column per answer -->
        <template v-else>
          <li v-for="column in s.columns.value" :key="keyOf(column.source)" class="grid grid-cols-1 items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_8rem] sm:gap-3">
            <span class="flex min-w-0 items-center gap-2 text-sm">
              <UIcon :name="sourceIcon(column.source)" class="size-4 shrink-0 text-muted" />
              <span class="truncate text-highlighted">{{ sourceLabel(column.source) }}</span>
            </span>
            <UInput :model-value="column.column" size="sm" class="w-full font-mono" dir="ltr" maxlength="63" spellcheck="false" :aria-label="t('destinations.columns.columnFor', { item: sourceLabel(column.source) })" @update:model-value="value => rename(keyOf(column.source), String(value))" />
            <code class="truncate font-mono text-[11px] text-muted" dir="ltr">{{ column.type }}</code>
          </li>
        </template>
      </ul>
    </div>

    <!-- New table: answers left out -->
    <UCollapsible v-if="!manualMode" class="flex flex-col gap-2">
      <UButton :label="t('destinations.columns.chooseAnswers')" icon="i-lucide-list-checks" trailing-icon="i-lucide-chevron-down" color="neutral" variant="link" size="sm" class="w-fit px-0" />
      <template #content>
        <div class="grid grid-cols-1 gap-2 pt-1 sm:grid-cols-2">
          <UCheckbox v-for="field in fields" :key="field.key" :model-value="!setup.skipped.value.includes(field.key)" :label="field.label" @update:model-value="value => toggleSkip(field.key, !!value)" />
        </div>
      </template>
    </UCollapsible>
  </div>
</template>

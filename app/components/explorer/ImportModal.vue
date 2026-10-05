<!--
  Import a CSV or Excel file into a table (F12 M3; Full access, the organisation's own tables).
  1. Pick the file (up to 5 MB, 50,000 rows); it is read on Formalie's servers. 2. Match each
  column to a file column (matched by name already) or leave it empty; the first rows show how
  they will land. 3. Import with a percentage; then how many rows were added, how many were
  skipped and why (row, column, problem). Nothing is added twice; recorded in the audit trail.
-->
<script setup lang="ts">
import type { TableStructure } from '#shared/types/explorer'

interface Preview {
  id: string
  headers: string[]
  sample: string[][]
  total: number
  mapping: Record<string, string | null>
}
interface ImportState {
  status: 'ready' | 'running' | 'done'
  progress: number
  total: number
  inserted: number
  failed: number
  errors: { row: number; column: string; problem: string }[]
}

const props = defineProps<{ sourceId: string; structure: TableStructure }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ done: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { number } = useFormat()

const file = ref<File | null>(null)
const reading = ref(false)
const preview = ref<Preview | null>(null)
const mapping = ref<Record<string, string | null>>({})
const state = ref<ImportState | null>(null)
const mappingErrors = ref<Record<string, string>>({})
const busy = computed(() => reading.value || state.value?.status === 'running')
watch(open, isOpen => {
  if (!isOpen) return
  file.value = null
  preview.value = null
  state.value = null
  mappingErrors.value = {}
})

const { open: pick, onChange } = useFileDialog({
  accept: '.csv,.xlsx,text/csv',
  multiple: false,
  reset: true,
})
onChange(async files => {
  const chosen = files?.[0]
  if (!chosen) return
  file.value = chosen
  if (chosen.size > 5 * 1024 * 1024) return void handle(new ApiError('FRM-DEST-1021', ''))
  reading.value = true
  try {
    const content = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result).split(',')[1] ?? '')
      reader.onerror = () => reject(reader.error)
      reader.readAsDataURL(chosen)
    })
    const { data } = await api.post<Preview>(`/datasources/${props.sourceId}/explorer/imports`, {
      schema: props.structure.schema,
      table: props.structure.name,
      file_name: chosen.name,
      content,
    })
    preview.value = data
    mapping.value = { ...data.mapping }
  } catch (error) {
    handle(error)
  } finally {
    reading.value = false
  }
})

const headerItems = computed(() => [
  { value: '', label: t('explorer.import.leaveEmpty') },
  ...(preview.value?.headers ?? []).map(header => ({ value: header, label: header })),
])
const needed = (name: string) => {
  const column = props.structure.columns.find(item => item.name === name)!
  return !column.nullable && !column.has_default
}
const sampleValue = (line: string[], column: string) => {
  const header = mapping.value[column]
  return header ? (line[preview.value!.headers.indexOf(header)] ?? '') : ''
}

async function run() {
  if (!preview.value) return
  mappingErrors.value = Object.fromEntries(
    props.structure.columns
      .filter(column => needed(column.name) && !mapping.value[column.name])
      .map(column => [column.name, t('explorer.problem.required')]),
  )
  if (Object.keys(mappingErrors.value).length) return
  try {
    state.value = (
      await api.post<ImportState>(`/explorer-imports/${preview.value.id}/run`, {
        mapping: Object.fromEntries(
          Object.entries(mapping.value).map(([key, value]) => [key, value || null]),
        ),
      })
    ).data
    while (state.value.status === 'running') {
      await new Promise(resolve => setTimeout(resolve, 400))
      state.value = (
        await api.get<ImportState>(`/explorer-imports/${preview.value.id}`, undefined, { background: true })
      ).data
    }
    emit('done')
  } catch (error) {
    handle(error)
    state.value = null
  }
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('explorer.import.title')"
    :description="`${structure.schema}.${structure.name}`"
    :dismissible="!busy"
    :ui="{ content: 'sm:max-w-3xl' }"
  >
    <template #body>
      <!-- 1. The file -->
      <div
        v-if="!preview"
        class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-default px-4 py-10 text-center"
      >
        <UIcon name="i-lucide-file-up" class="size-8 text-muted" />
        <p class="text-sm text-highlighted">{{ t('explorer.import.pick') }}</p>
        <p class="text-xs text-muted">{{ t('explorer.import.pickDesc') }}</p>
        <UButton
          :label="file ? file.name : t('explorer.import.choose')"
          icon="i-lucide-paperclip"
          color="neutral"
          :loading="reading"
          @click="pick()"
        />
      </div>

      <!-- 3. Done -->
      <div v-else-if="state" class="flex flex-col gap-4" role="status">
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between text-sm">
            <span class="font-medium text-highlighted">{{
              state.status === 'done'
                ? t('explorer.import.finished')
                : t('explorer.import.running', { n: number(state.total) })
            }}</span>
            <span class="text-muted tabular-nums">{{ state.progress }}%</span>
          </div>
          <UProgress :model-value="state.progress" color="neutral" size="sm" />
        </div>
        <template v-if="state.status === 'done'">
          <div class="grid grid-cols-2 gap-2">
            <div class="rounded-lg border border-default px-3 py-2">
              <p class="text-[11px] text-muted">{{ t('explorer.import.added') }}</p>
              <p class="text-lg font-semibold text-highlighted tabular-nums">{{ number(state.inserted) }}</p>
            </div>
            <div class="rounded-lg border border-default px-3 py-2">
              <p class="text-[11px] text-muted">{{ t('explorer.import.skipped') }}</p>
              <p
                class="text-lg font-semibold tabular-nums"
                :class="state.failed ? 'text-error' : 'text-highlighted'"
              >
                {{ number(state.failed) }}
              </p>
            </div>
          </div>
          <div v-if="state.errors.length" class="flex flex-col gap-2">
            <p class="text-xs text-muted">{{ t('explorer.import.whySkipped') }}</p>
            <ul
              class="max-h-56 divide-y divide-default overflow-y-auto rounded-lg border border-default text-sm"
            >
              <li
                v-for="item in state.errors"
                :key="`${item.row}${item.column}`"
                class="flex flex-wrap items-center gap-2 px-3 py-1.5"
              >
                <span class="text-xs text-muted tabular-nums">{{
                  t('explorer.import.rowN', { n: item.row })
                }}</span>
                <code class="font-mono text-xs text-highlighted" dir="ltr">{{ item.column }}</code>
                <span class="text-xs text-error">{{
                  t(`explorer.problem.${item.problem}`, { max: '' })
                }}</span>
              </li>
            </ul>
          </div>
        </template>
      </div>

      <!-- 2. Matching -->
      <div v-else class="flex flex-col gap-4">
        <p class="text-sm text-default">
          {{
            t('explorer.import.found', { n: number(preview.total), file: file?.name ?? '' }, preview.total)
          }}
        </p>
        <div class="overflow-hidden rounded-lg border border-default">
          <div
            class="hidden grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] gap-3 border-b border-default bg-elevated/50 px-3 py-2 text-xs font-medium text-muted sm:grid"
          >
            <span>{{ t('destinations.columns.column') }}</span>
            <span>{{ t('explorer.import.fileColumn') }}</span>
            <span>{{ t('explorer.import.firstRow') }}</span>
          </div>
          <ul class="max-h-80 divide-y divide-default overflow-y-auto">
            <li
              v-for="column in structure.columns"
              :key="column.name"
              class="grid grid-cols-1 items-center gap-2 px-3 py-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)] sm:gap-3"
              :class="mappingErrors[column.name] ? 'bg-error/5' : ''"
            >
              <span class="flex min-w-0 items-center gap-1">
                <code class="truncate font-mono text-xs text-highlighted" dir="ltr">{{ column.name }}</code>
                <span
                  v-if="needed(column.name)"
                  class="text-error"
                  :title="t('destinations.columns.required')"
                  >*</span
                >
              </span>
              <USelect
                :model-value="mapping[column.name] ?? ''"
                :items="headerItems"
                value-key="value"
                size="sm"
                class="w-full"
                :aria-label="t('destinations.columns.fillsFor', { column: column.name })"
                @update:model-value="value => (mapping[column.name] = String(value) || null)"
              />
              <span class="truncate text-xs text-muted" dir="auto">{{
                preview.sample[0] ? sampleValue(preview.sample[0], column.name) || '–' : '–'
              }}</span>
            </li>
          </ul>
        </div>
        <UAlert
          v-if="Object.keys(mappingErrors).length"
          icon="i-lucide-circle-x"
          color="error"
          variant="subtle"
          :title="t('explorer.import.needed', { columns: Object.keys(mappingErrors).join(', ') })"
        />
        <p class="flex gap-1.5 text-xs text-muted">
          <UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" /> {{ t('explorer.import.note') }}
        </p>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          :label="state?.status === 'done' ? t('common.close') : t('common.cancel')"
          color="neutral"
          :variant="state?.status === 'done' ? 'solid' : 'outline'"
          :disabled="busy"
          @click="open = false"
        />
        <UButton
          v-if="preview && !state"
          :label="t('explorer.import.start', { n: number(preview.total) }, preview.total)"
          icon="i-lucide-file-up"
          color="neutral"
          @click="run"
        />
      </div>
    </template>
  </AppModal>
</template>

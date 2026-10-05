<!--
  Query results (F12 M4), built for raw output rather than a list page: a row-number gutter, slim
  monospaced rows with column lines, NULL dimmed, a sticky header, columns resized by dragging the
  line between headers (double-click fits, ← / → when focused), a status line (rows, time) and
  paging. Right-click a cell: copy the value, the row (JSON) or the column's name.
-->
<script setup lang="ts">
import type { QueryResult } from '#shared/types/query'

const props = defineProps<{ result: QueryResult }>()
const emit = defineEmits<{ page: [page: number] }>()
const { t } = useI18n()
const { number } = useFormat()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

const START = 160
const MIN = 56
const widths = ref<number[]>([])
watch(
  () => props.result.columns.map(column => column.name).join('\u0000'),
  () => (widths.value = props.result.columns.map(() => START)),
  { immediate: true },
)
const total = computed(() => 56 + widths.value.reduce((sum, width) => sum + width, 0))
const offset = computed(() => (props.result.page - 1) * props.result.page_size)

// Dragging a header's edge
let drag: { index: number; start: number; width: number } | null = null
function down(event: PointerEvent, index: number) {
  event.preventDefault()
  drag = { index, start: event.clientX, width: widths.value[index]! }
  ;(event.target as HTMLElement).setPointerCapture(event.pointerId)
}
function move(event: PointerEvent) {
  if (!drag) return
  const rtl = getComputedStyle(event.target as Element).direction === 'rtl'
  widths.value[drag.index] = Math.max(MIN, Math.min(1200, drag.width + (event.clientX - drag.start) * (rtl ? -1 : 1)))
}
const up = () => (drag = null)
const root = useTemplateRef<HTMLElement>('root')
function fit(index: number) {
  const cells = [...(root.value?.querySelectorAll(`[data-col="${index}"]`) ?? [])] as HTMLElement[]
  widths.value[index] = Math.max(MIN, Math.min(1200, Math.max(...cells.map(cell => (cell.firstElementChild as HTMLElement | null)?.scrollWidth ?? 0)) + 24))
}
function key(event: KeyboardEvent, index: number) {
  const direction = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
  if (!direction) return
  event.preventDefault()
  widths.value[index] = Math.max(MIN, widths.value[index]! + direction * (event.shiftKey ? 64 : 16))
}

const asText = (value: unknown) => (value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value))
function copyText(text: string) {
  void copy(text)
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
useContextMenu().register(root, target => {
  const cell = target.closest('[data-cell]')
  const head = target.closest('[data-col-head]')
  if (head) {
    const column = props.result.columns[Number(head.getAttribute('data-col-head'))]
    return column ? [[{ label: t('explorer.ddl.copyName'), icon: 'i-lucide-copy', onSelect: () => copyText(column.name) }]] : null
  }
  if (!cell) return null
  const [rowIndex, colIndex] = cell.getAttribute('data-cell')!.split(':').map(Number) as [number, number]
  const row = props.result.rows[rowIndex]
  if (!row) return null
  const record = Object.fromEntries(props.result.columns.map((column, index) => [column.name, row[index] ?? null]))
  return [
    [
      { label: t('explorer.menu.copyValue'), icon: 'i-lucide-copy', disabled: row[colIndex] == null, onSelect: () => copyText(asText(row[colIndex])) },
      { label: t('explorer.copyRow'), icon: 'i-lucide-braces', onSelect: () => copyText(JSON.stringify(record, null, 2)) },
      { label: t('explorer.ddl.copyName'), icon: 'i-lucide-columns-3', onSelect: () => copyText(props.result.columns[colIndex]?.name ?? '') },
    ],
  ]
})
const pages = computed(() => (props.result.total ? Math.ceil(props.result.total / props.result.page_size) : 1))
</script>

<template>
  <div ref="root" class="flex min-h-0 flex-1 flex-col">
    <div class="min-h-0 flex-1 overflow-auto">
      <table class="table-fixed border-separate border-spacing-0 font-mono text-xs" :style="{ width: `${total}px` }">
        <thead class="sticky top-0 z-10 bg-elevated">
          <tr>
            <th class="sticky start-0 z-10 h-8 w-14 border-e border-b border-default bg-elevated px-2 text-end font-normal text-dimmed" aria-label="#">#</th>
            <th
              v-for="(column, index) in result.columns"
              :key="`${column.name}${index}`"
              :data-col-head="index"
              class="relative h-8 border-e border-b border-default px-3 text-start font-medium whitespace-nowrap text-highlighted"
              :style="{ width: `${widths[index]}px` }"
            >
              <div class="truncate" :title="column.name">{{ column.name }}</div>
              <span
                role="separator"
                tabindex="0"
                aria-orientation="vertical"
                :aria-label="t('dataView.resizeColumn', { name: column.name })"
                :aria-valuenow="widths[index]"
                :title="t('dataView.resizeHint')"
                class="absolute inset-y-0 -end-1.5 z-10 flex w-3 cursor-col-resize touch-none justify-center select-none after:my-1.5 after:w-px after:rounded-full after:bg-(--ui-border-accented) hover:after:w-0.5 hover:after:bg-(--ui-border-inverted) focus-visible:outline-none focus-visible:after:w-0.5 focus-visible:after:bg-(--ui-border-inverted)"
                @pointerdown="down($event, index)"
                @pointermove="move"
                @pointerup="up"
                @pointercancel="up"
                @dblclick="fit(index)"
                @keydown="key($event, index)"
              />
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, rowIndex) in result.rows" :key="rowIndex" class="hover:bg-elevated/50">
            <td class="sticky start-0 h-7 border-e border-b border-default bg-default px-2 text-end text-dimmed tabular-nums">{{ number(offset + rowIndex + 1) }}</td>
            <td v-for="(value, colIndex) in row" :key="colIndex" :data-col="colIndex" :data-cell="`${rowIndex}:${colIndex}`" class="h-7 overflow-hidden border-e border-b border-default px-3 whitespace-nowrap">
              <ExplorerCell :value="value" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-default px-3 py-1.5 text-xs text-muted">
      <span class="tabular-nums">
        {{ result.total === 0 ? t('query.noRows') : t('query.showing', { from: number(offset + 1), to: number(offset + result.rows.length), total: `${number(result.total ?? 0)}${result.capped ? '+' : ''}` }) }}
        · {{ t('query.took', { ms: number(result.duration_ms) }) }}
      </span>
      <UPagination
        v-if="pages > 1"
        :page="result.page"
        :total="result.total ?? 0"
        :items-per-page="result.page_size"
        :sibling-count="1"
        :show-edges="!result.capped"
        size="xs"
        @update:page="(page: number) => emit('page', page)"
      />
    </div>
  </div>
</template>

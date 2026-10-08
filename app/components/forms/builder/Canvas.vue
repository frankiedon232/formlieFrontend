<!--
  Builder canvas (FRONTEND-SPEC §6, centre): page tabs (PageTabs) + the page as respondents will see
  it, rows on a 12-column grid. The page fills the screen's height and grows with its content, with
  no title block (owner 2026-10-08: the name lives on the tab; sections and paragraphs carry content).
  Drag fields by their handle, within a row, between rows, or between rows to give them their own
  row; drop palette fields anywhere. Click an empty spot to add a field right there (QuickAdd): above
  or between rows it gets its own row, beside the fields of a row with room it joins that row.
-->
<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import type { FieldType } from '#shared/utils/forms/fields'
import { allFields } from '#shared/utils/forms/build'
import { fitAnswer } from '#shared/utils/forms/cascade'

defineProps<{ issues?: Record<string, string>; minHeight?: string }>()
/** Ask the page to show the field list (drawer on phones / tablets, palette search on laptops). */
const emit = defineEmits<{ addField: [] }>()
const { t } = useI18n()
const builder = useBuilder()
const { page, pages, selected } = builder

const labelPosition = computed(() => builder.schema.value?.settings?.label_position ?? 'top')
// Field icons (Form settings), shown on the canvas as respondents will see them
provide(RENDERER_ICONS, computed(() => builder.schema.value?.settings?.field_icons !== false))
const labelWidth = computed(() => labelColumnWidth(builder.fields.value))
// Lists with levels behave on the canvas as in the form (owner 2026-10-07): what you try in a level
// narrows the next, and a changed choice clears what no longer fits (nothing is stored)
const trials = ref<Record<string, unknown>>({})
const fieldsById = computed(() => new Map((builder.schema.value ? allFields(builder.schema.value) : []).map(field => [field.id, field])))
provide(RENDERER_ANSWERS, { answers: trials, fieldsById })
watchEffect(() => {
  for (const field of fieldsById.value.values()) {
    if (!field.option_parent || trials.value[field.key] == null) continue
    const fitted = fitAnswer(field, fieldsById.value, trials.value)
    if (JSON.stringify(fitted ?? null) !== JSON.stringify(trials.value[field.key] ?? null)) trials.value[field.key] = fitted ?? null
  }
})
// Drop placeholder labels (CSS `content` needs a quoted string).
const dropNewRow = computed(() => JSON.stringify(`↓ ${t('builder.drop.newRow')}`))
const dropBeside = computed(() => JSON.stringify(`→ ${t('builder.drop.beside')}`))
function dragStart() {
  builder.history.record()
  builder.dragging.value = true
}
function dragEnd() {
  builder.dragging.value = false
  afterDrop()
}
const pageIndex = computed(() => pages.value.findIndex(p => p.id === page.value?.id))
const afterDrop = () => page.value && builder.normaliseRows(page.value)
const QUICK: FieldType[] = ['short_text', 'email', 'radio', 'long_text']

// ── Click to add ────────────────────────────────────────────────────────────────────
const rowsEl = useTemplateRef<{ $el?: HTMLElement } | HTMLElement>('rows')
const quick = reactive({ open: false, x: 0, y: 0, rowIndex: 0, beside: false })
/** Where a click lands: beside the fields of a row with room, else a new row above the first row below it. */
function spotOf(event: MouseEvent) {
  const root = rowsEl.value && '$el' in rowsEl.value ? rowsEl.value.$el : (rowsEl.value as HTMLElement | null)
  const rows = root ? [...root.querySelectorAll<HTMLElement>(':scope > [data-row]')] : []
  for (const [index, row] of rows.entries()) {
    const box = row.getBoundingClientRect()
    if (event.clientY < box.top) return { rowIndex: index, beside: false }
    if (event.clientY <= box.bottom) {
      const used = page.value?.rows[index]?.fields.reduce((sum, field) => sum + (field.width ?? 12), 0) ?? 12
      const right = Math.max(...[...row.children].map(child => child.getBoundingClientRect().right))
      const after = document.dir === 'rtl' ? event.clientX < Math.min(...[...row.children].map(child => child.getBoundingClientRect().left)) : event.clientX > right
      return used < 12 && after ? { rowIndex: index, beside: true } : { rowIndex: index + 1, beside: false }
    }
  }
  return { rowIndex: rows.length, beside: false }
}
function onPageClick(event: MouseEvent) {
  // First click on the page clears a selection; the next one adds
  if (selected.value.length) return void (selected.value = [])
  if ((event.target as HTMLElement).closest('button, a, input, textarea, [role="combobox"]')) return
  Object.assign(quick, { x: event.clientX, y: event.clientY, ...spotOf(event), open: true })
}
function quickPick(type: FieldType) {
  if (!page.value) return
  const target = { pageId: page.value.id, rowIndex: quick.rowIndex }
  if (quick.beside) builder.addToRow(type, target)
  else builder.addField(type, target)
}
</script>

<template>
  <div class="flex min-h-full flex-col gap-4" @click="selected = []">
    <FormsBuilderPageTabs @add-field="emit('addField')" />

    <UCard
      v-if="page"
      class="w-full cursor-copy transition-[outline-color] @container/form"
      :class="[FORM_RADIUS, minHeight, builder.dragging.value ? 'outline-2 outline-offset-4 outline-(--ui-border-accented) outline-dashed' : '']"
      :style="{ '--form-label-w': labelWidth }"
      :ui="{ root: 'flex flex-col', body: 'relative flex flex-1 flex-col gap-4 p-3 sm:p-5' }"
      @click.stop="onPageClick"
    >
      <div v-if="pages.length > 1" class="flex flex-col gap-1.5" @click.stop>
        <div class="flex justify-between text-xs text-muted">
          <span>{{ t('builder.page.stepOf', { n: pageIndex + 1, total: pages.length }) }}</span>
          <span>{{ Math.round(((pageIndex + 1) / pages.length) * 100) }}%</span>
        </div>
        <UProgress :model-value="pageIndex + 1" :max="pages.length" color="neutral" size="xs" />
      </div>

      <VueDraggable
        ref="rows"
        v-model="page.rows"
        :group="{ name: 'fields', pull: false, put: true }"
        handle="[data-no-row-drag]"
        :animation="150"
        :ghost-class="DROP_GHOST"
        class="flex min-h-24 flex-1 flex-col gap-1"
        :class="DROP_ZONE"
        :style="{ '--drop-label': dropNewRow }"
        @start="dragStart"
        @add="afterDrop"
        @end="dragEnd"
      >
        <VueDraggable
          v-for="row in page.rows"
          :key="row.id"
          v-model="row.fields"
          group="fields"
          handle="[data-drag-handle]"
          :animation="150"
          :ghost-class="DROP_GHOST"
          class="grid cursor-default grid-cols-12 gap-x-2 gap-y-1"
          :class="DROP_ZONE_ROW"
          :style="{ '--drop-label': dropBeside }"
          data-row
          @start="dragStart"
          @end="dragEnd"
        >
          <div v-for="field in row.fields" :key="field.id" class="col-span-12 @container" :class="FIELD_SPAN[field.width ?? 12]">
            <FormsBuilderFieldShell :field="field" :label-position="labelPosition" :selected="selected.includes(field.id)" :issue="issues?.[field.id]" @remove="builder.removeWithUndo([field.id])" />
          </div>
        </VueDraggable>
      </VueDraggable>

      <!-- Empty page: centred in the page; drags pass through to the drop area underneath, only the buttons take clicks -->
      <div v-if="!page.rows.length" class="pointer-events-none absolute inset-0 flex items-center justify-center p-4">
        <div class="flex flex-col items-center gap-3 rounded-lg border border-dashed border-default px-4 py-10 text-center">
          <span class="flex size-14 items-center justify-center rounded-2xl border border-primary/15 bg-primary/5" aria-hidden="true">
            <span class="flex size-10 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 shadow-sm"><UIcon name="i-lucide-mouse-pointer-click" class="size-5 text-primary" /></span>
          </span>
          <div>
            <p class="font-medium text-highlighted">{{ t('builder.empty.title') }}</p>
            <p class="text-sm text-muted">{{ t('builder.empty.desc') }}</p>
          </div>
          <div class="pointer-events-auto flex flex-wrap justify-center gap-2" @click.stop>
            <UButton v-for="type in QUICK" :key="type" :icon="fieldIcon(type)" :label="t(`builder.field.${type}`)" color="neutral" variant="outline" size="sm" @click="builder.addField(type)" />
          </div>
        </div>
      </div>

      <UButton v-if="page.rows.length" :label="t('builder.palette.title')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" class="self-end border border-dashed border-accented bg-transparent text-muted ring-0 hover:text-highlighted" @click.stop="emit('addField')" />
    </UCard>

    <FormsBuilderQuickAdd v-model:open="quick.open" :x="quick.x" :y="quick.y" @pick="quickPick" />
  </div>
</template>

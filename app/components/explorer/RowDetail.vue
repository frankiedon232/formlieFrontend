<!--
  One row in a panel from the side (F12 M3, detail panel model): its key and table, every column
  with its type and full value (JSON laid out), a copy button per value and "Copy row" (JSON);
  a column that points at another table opens it. Previous (K) · position · Next (J). Esc closes.
-->
<script setup lang="ts">
import type { TableRow, TableStructure } from '#shared/types/explorer'

const props = defineProps<{
  row: TableRow | null
  rows: TableRow[]
  structure: TableStructure
  busy?: boolean
}>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{
  go: [row: TableRow]
  table: [ref: { schema: string; table: string }]
  edit: [row: TableRow]
  remove: [row: TableRow]
}>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

const index = computed(() => (props.row ? props.rows.findIndex(item => item.__key === props.row!.__key) : -1))
const prev = computed(() => (index.value > 0 ? props.rows[index.value - 1] : null))
const next = computed(() =>
  index.value >= 0 && index.value < props.rows.length - 1 ? props.rows[index.value + 1] : null,
)
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})
const asText = (value: unknown) =>
  value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
function copyValue(value: unknown) {
  void copy(asText(value))
  toast.add({ title: t('common.copied'), color: 'success', icon: 'i-lucide-check' })
}
function copyRow() {
  if (!props.row) return
  const { __key: _key, ...values } = props.row
  void copy(JSON.stringify(values, null, 2))
  toast.add({ title: t('explorer.rowCopied'), color: 'success', icon: 'i-lucide-check' })
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }"
    :title="t('explorer.row', { key: row?.__key ?? '' })"
    :ui="{
      content: 'w-full sm:max-w-2xl',
      header: 'border-b-0 pb-2',
      body: 'flex flex-col gap-3 pb-56',
      footer:
        'pointer-events-none absolute inset-x-0 bottom-0 justify-center border-t-0 bg-gradient-to-t from-(--ui-bg) via-(--ui-bg)/85 to-transparent pt-10 pb-4',
    }"
  >
    <template #header>
      <div class="flex w-full items-start gap-3.5">
        <span class="flex size-12 shrink-0 items-center justify-center rounded-xl border border-default"
          ><UIcon
            :name="structure.formalie ? 'i-lucide-inbox' : 'i-lucide-table-2'"
            class="size-6 text-highlighted"
        /></span>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <h2 class="truncate font-mono text-lg leading-tight font-semibold text-highlighted" dir="ltr">
            {{ row?.__key }}
          </h2>
          <p class="truncate font-mono text-xs text-muted" dir="ltr">
            {{ structure.schema }}.{{ structure.name }}
          </p>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <template v-if="!structure.read_only && row">
            <UButton
              :label="t('explorer.edit')"
              icon="i-lucide-pencil"
              color="neutral"
              size="sm"
              :disabled="busy"
              @click="emit('edit', row)"
            />
            <UButton
              icon="i-lucide-trash-2"
              color="error"
              variant="soft"
              size="sm"
              square
              :loading="busy"
              :aria-label="t('explorer.deleteRow')"
              @click="emit('remove', row)"
            />
          </template>
          <UButton
            :label="t('explorer.copyRow')"
            icon="i-lucide-braces"
            color="neutral"
            variant="outline"
            size="sm"
            class="hidden sm:inline-flex"
            @click="copyRow"
          />
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="soft"
            size="sm"
            square
            class="rounded-full"
            :aria-label="t('common.close')"
            @click="open = false"
          />
        </div>
      </div>
    </template>

    <template #body>
      <dl v-if="row" class="flex flex-col divide-y divide-default rounded-lg border border-default">
        <div
          v-for="column in structure.columns"
          :key="column.name"
          class="grid grid-cols-1 gap-1 px-3 py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)_auto] sm:gap-3"
        >
          <dt class="flex min-w-0 flex-col">
            <span class="flex items-center gap-1 truncate font-mono text-xs text-highlighted" dir="ltr">
              <UIcon v-if="column.primary" name="i-lucide-key-round" class="size-3 shrink-0 text-muted" />
              {{ column.name }}
            </span>
            <span class="truncate font-mono text-[10px] text-dimmed" dir="ltr">{{ column.type }}</span>
          </dt>
          <dd class="min-w-0 text-sm text-default">
            <ExplorerCell :value="row[column.name]" full />
            <UButton
              v-if="column.references && row[column.name] != null"
              :label="t('explorer.openReferenced', { table: column.references.table })"
              icon="i-lucide-arrow-up-right"
              color="neutral"
              variant="link"
              size="xs"
              class="mt-1 px-0 rtl:[&_.iconify]:-scale-x-100"
              @click="emit('table', { schema: column.references.schema, table: column.references.table })"
            />
          </dd>
          <UButton
            v-if="row[column.name] != null"
            icon="i-lucide-copy"
            color="neutral"
            variant="ghost"
            size="xs"
            class="self-start"
            :aria-label="t('explorer.copyValue', { column: column.name })"
            @click="copyValue(row[column.name])"
          />
        </div>
      </dl>
    </template>

    <template #footer>
      <nav
        class="pointer-events-auto flex items-center gap-1 rounded-full border border-default bg-default/95 p-1 shadow-lg backdrop-blur"
        :aria-label="t('explorer.navigate')"
      >
        <UButton
          :label="t('responses.detail.prevShort')"
          icon="i-lucide-arrow-up"
          color="neutral"
          variant="ghost"
          size="sm"
          class="rounded-full"
          :disabled="!prev"
          :aria-label="t('explorer.previous')"
          @click="prev && emit('go', prev)"
        >
          <template #trailing><UKbd value="K" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
        <span v-if="index >= 0" class="px-2 text-xs text-muted tabular-nums">{{
          t('responses.detail.position', { n: index + 1, total: rows.length })
        }}</span>
        <UButton
          :label="t('responses.detail.nextShort')"
          icon="i-lucide-arrow-down"
          color="neutral"
          variant="solid"
          size="sm"
          class="rounded-full"
          :disabled="!next"
          :aria-label="t('explorer.next')"
          @click="next && emit('go', next)"
        >
          <template #trailing><UKbd value="J" size="sm" class="hidden sm:inline-flex" /></template>
        </UButton>
      </nav>
    </template>
  </USlideover>
</template>

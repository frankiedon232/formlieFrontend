<!--
  Builder canvas (FRONTEND-SPEC §6, centre): page tabs (design segmented control) + the page as
  respondents will see it, rows on a 12-column grid. Drag fields by their handle, within a row,
  between rows, or between rows to give them their own row; drop palette fields anywhere.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import { VueDraggable } from 'vue-draggable-plus'
import type { FieldType } from '#shared/utils/forms/fields'
import { allFields } from '#shared/utils/forms/build'
import { fitAnswer } from '#shared/utils/forms/cascade'

defineProps<{ issues?: Record<string, string> }>()
/** Ask the page to show the field list (drawer on phones / tablets, palette search on laptops). */
const emit = defineEmits<{ addField: [] }>()
const { t } = useI18n()
const confirm = useConfirm()
const builder = useBuilder()
const { page, pages, pageId, selected } = builder

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
const tabs = computed(() =>
  pages.value.map((p, i) => ({ value: p.id, label: p.title || t('builder.page.default', { n: i + 1 }) })),
)
const pageIndex = computed(() => pages.value.findIndex(p => p.id === page.value?.id))

const pageMenu = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('builder.page.moveLeft'),
      icon: 'i-lucide-arrow-left',
      disabled: pageIndex.value <= 0,
      onSelect: () => page.value && builder.movePage(page.value.id, -1),
    },
    {
      label: t('builder.page.moveRight'),
      icon: 'i-lucide-arrow-right',
      disabled: pageIndex.value >= pages.value.length - 1,
      onSelect: () => page.value && builder.movePage(page.value.id, 1),
    },
  ],
  [
    {
      label: t('builder.page.delete'),
      icon: 'i-lucide-trash-2',
      color: 'error',
      disabled: pages.value.length < 2,
      onSelect: removePage,
    },
  ],
])

async function removePage() {
  if (!page.value) return
  const count = page.value.rows.reduce((n, row) => n + row.fields.length, 0)
  if (
    count &&
    !(await confirm({
      title: t('builder.page.deleteTitle'),
      description: t('builder.page.deleteDesc', { count }, count),
      danger: true,
      confirmLabel: t('builder.page.delete'),
    }))
  )
    return
  builder.removePage(page.value.id)
}

const QUICK: FieldType[] = ['short_text', 'email', 'radio', 'long_text']
const afterDrop = () => page.value && builder.normaliseRows(page.value)
</script>

<template>
  <div class="flex min-h-full flex-col gap-4" @click="selected = []">
    <div class="flex flex-wrap items-center gap-2" @click.stop>
      <UTabs
        :model-value="pageId ?? undefined"
        :items="tabs"
        :content="false"
        color="neutral"
        size="sm"
        :ui="{ ...SEGMENTED_UI, list: `${SEGMENTED_UI.list} max-w-full overflow-x-auto` }"
        :aria-label="t('builder.page.tabs')"
        class="min-w-0"
        @update:model-value="v => (pageId = String(v))"
      />
      <UButton
        :label="t('builder.page.add')"
        icon="i-lucide-plus"
        color="neutral"
        variant="outline"
        size="sm"
        @click="builder.addPage()"
      />
      <UButton
        :label="t('builder.palette.title')"
        icon="i-lucide-plus"
        color="neutral"
        size="sm"
        class="ms-auto lg:hidden"
        @click="emit('addField')"
      />
      <UDropdownMenu :items="pageMenu" :content="{ align: 'start' }">
        <UButton
          icon="i-lucide-ellipsis"
          color="neutral"
          variant="outline"
          size="sm"
          square
          :aria-label="t('builder.page.menu')"
        />
      </UDropdownMenu>
    </div>

    <UCard
      v-if="page"
      class="w-full transition-[outline-color] @container/form"
      :class="[FORM_RADIUS, builder.dragging.value ? 'outline-2 outline-offset-4 outline-(--ui-border-accented) outline-dashed' : '']"
      :style="{ '--form-label-w': labelWidth }"
      :ui="{ body: 'flex flex-col gap-4 p-3 sm:p-5' }"
    >
      <div v-if="pages.length > 1" class="flex flex-col gap-1.5" @click.stop>
        <div class="flex justify-between text-xs text-muted">
          <span>{{ t('builder.page.stepOf', { n: pageIndex + 1, total: pages.length }) }}</span>
          <span>{{ Math.round(((pageIndex + 1) / pages.length) * 100) }}%</span>
        </div>
        <UProgress :model-value="pageIndex + 1" :max="pages.length" color="neutral" size="xs" />
      </div>

      <UInput
        :model-value="page.title"
        variant="ghost"
        size="xl"
        :placeholder="t('builder.page.default', { n: pageIndex + 1 })"
        :aria-label="t('builder.page.title')"
        :ui="{ base: 'px-0 text-xl font-semibold text-highlighted' }"
        @click.stop
        @update:model-value="v => builder.renamePage(page!.id, String(v))"
      />

      <VueDraggable
        v-model="page.rows"
        :group="{ name: 'fields', pull: false, put: true }"
        handle="[data-no-row-drag]"
        :animation="150"
        :ghost-class="DROP_GHOST"
        class="flex min-h-24 flex-col gap-1"
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
          class="grid grid-cols-12 gap-x-2 gap-y-1"
          :class="DROP_ZONE_ROW"
          :style="{ '--drop-label': dropBeside }"
          @start="dragStart"
          @end="dragEnd"
        >
          <div
            v-for="field in row.fields"
            :key="field.id"
            class="col-span-12 @container"
            :class="FIELD_SPAN[field.width ?? 12]"
          >
            <FormsBuilderFieldShell
              :field="field"
              :label-position="labelPosition"
              :selected="selected.includes(field.id)"
              :issue="issues?.[field.id]"
              @remove="builder.removeWithUndo([field.id])"
            />
          </div>
        </VueDraggable>
      </VueDraggable>

      <UButton
        v-if="page.rows.length"
        :label="t('builder.palette.title')"
        icon="i-lucide-plus"
        color="neutral"
        variant="outline"
        size="sm"
        class="self-end border border-dashed border-accented bg-transparent text-muted ring-0 hover:text-highlighted"
        @click.stop="emit('addField')"
      />

      <div
        v-if="!page.rows.length"
        class="pointer-events-none -mt-28 flex flex-col items-center gap-3 rounded-lg border border-dashed border-default px-4 py-10 text-center"
      >
        <!-- Lets drags pass through to the drop area underneath; only the buttons take clicks. -->
        <!-- The same layered tile as every empty state (AppEmpty) -->
        <span class="flex size-14 items-center justify-center rounded-2xl border border-default bg-elevated/40" aria-hidden="true">
          <span class="flex size-10 items-center justify-center rounded-xl border border-default bg-default shadow-sm"><UIcon name="i-lucide-mouse-pointer-click" class="size-5 text-highlighted" /></span>
        </span>
        <div>
          <p class="font-medium text-highlighted">{{ t('builder.empty.title') }}</p>
          <p class="text-sm text-muted">{{ t('builder.empty.desc') }}</p>
        </div>
        <div class="pointer-events-auto flex flex-wrap justify-center gap-2" @click.stop>
          <UButton
            v-for="type in QUICK"
            :key="type"
            :icon="fieldIcon(type)"
            :label="t(`builder.field.${type}`)"
            color="neutral"
            variant="outline"
            size="sm"
            @click="builder.addField(type)"
          />
        </div>
      </div>
    </UCard>
  </div>
</template>

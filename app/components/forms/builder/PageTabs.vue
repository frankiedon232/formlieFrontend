<!--
  Builder page tabs (owner 2026-10-08): the pages as tabs, the open page renamed in place with the
  pencil (or a double-click on the tabs; Enter saves, Esc cancels), Add page and the page menu (move,
  delete). The page name lives here only; the page itself stays clear for the form's content.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

const emit = defineEmits<{ addField: [] }>()
const { t } = useI18n()
const confirm = useConfirm()
const builder = useBuilder()
const { page, pages, pageId } = builder
// Large screens: show / hide the Fields and Settings panes for a wider canvas
const panes = useBuilderPanes()

const tabs = computed(() => pages.value.map((p, i) => ({ value: p.id, label: p.title || t('builder.page.default', { n: i + 1 }) })))
const pageIndex = computed(() => pages.value.findIndex(p => p.id === page.value?.id))

// Renaming the open page
const renaming = ref(false)
const draft = ref('')
const input = useTemplateRef<{ inputRef?: HTMLInputElement }>('rename')
async function startRename() {
  if (!page.value) return
  draft.value = page.value.title || t('builder.page.default', { n: pageIndex.value + 1 })
  renaming.value = true
  await nextTick()
  input.value?.inputRef?.select()
}
function finishRename(save: boolean) {
  if (save && page.value) builder.renamePage(page.value.id, draft.value.trim())
  renaming.value = false
}

const pageMenu = computed<DropdownMenuItem[][]>(() => [
  [
    { label: t('builder.page.rename'), icon: 'i-lucide-pencil', onSelect: () => void startRename() },
    { label: t('builder.page.moveLeft'), icon: 'i-lucide-arrow-left', disabled: pageIndex.value <= 0, onSelect: () => page.value && builder.movePage(page.value.id, -1) },
    { label: t('builder.page.moveRight'), icon: 'i-lucide-arrow-right', disabled: pageIndex.value >= pages.value.length - 1, onSelect: () => page.value && builder.movePage(page.value.id, 1) },
  ],
  [{ label: t('builder.page.delete'), icon: 'i-lucide-trash-2', color: 'error', disabled: pages.value.length < 2, onSelect: removePage }],
])
async function removePage() {
  if (!page.value) return
  const count = page.value.rows.reduce((n, row) => n + row.fields.length, 0)
  if (count && !(await confirm({ title: t('builder.page.deleteTitle'), description: t('builder.page.deleteDesc', { count }, count), danger: true, confirmLabel: t('builder.page.delete') }))) return
  builder.removePage(page.value.id)
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2" @click.stop>
    <UTooltip :text="panes.fields.value ? t('builder.pane.hideFields') : t('builder.pane.showFields')">
      <UButton :icon="panes.fields.value ? 'i-lucide-panel-left-close' : 'i-lucide-panel-left-open'" color="neutral" variant="ghost" size="sm" square class="hidden lg:inline-flex rtl:-scale-x-100" :aria-label="panes.fields.value ? t('builder.pane.hideFields') : t('builder.pane.showFields')" :aria-pressed="panes.fields.value" @click="panes.fields.value = !panes.fields.value" />
    </UTooltip>
    <UInput
      v-if="renaming"
      ref="rename"
      v-model="draft"
      size="sm"
      maxlength="120"
      class="w-56"
      :aria-label="t('builder.page.title')"
      @keydown.enter.prevent="finishRename(true)"
      @keydown.esc.stop.prevent="finishRename(false)"
      @blur="finishRename(true)"
    />
    <UTabs
      v-else
      :model-value="pageId ?? undefined"
      :items="tabs"
      :content="false"
      color="neutral"
      size="sm"
      :ui="{ ...SEGMENTED_UI, list: `${SEGMENTED_UI.list} max-w-full overflow-x-auto` }"
      :aria-label="t('builder.page.tabs')"
      class="min-w-0"
      @update:model-value="v => (pageId = String(v))"
      @dblclick="startRename"
    />
    <UTooltip v-if="!renaming" :text="t('builder.page.rename')">
      <UButton icon="i-lucide-pencil" color="neutral" variant="ghost" size="sm" square :aria-label="t('builder.page.rename')" @click="startRename" />
    </UTooltip>
    <UButton :label="t('builder.page.add')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" @click="builder.addPage()" />
    <UButton :label="t('builder.palette.title')" icon="i-lucide-plus" color="neutral" size="sm" class="ms-auto lg:hidden" @click="emit('addField')" />
    <UDropdownMenu :items="pageMenu" :content="{ align: 'start' }">
      <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="sm" square :aria-label="t('builder.page.menu')" />
    </UDropdownMenu>
    <UTooltip :text="panes.settings.value ? t('builder.pane.hideSettings') : t('builder.pane.showSettings')">
      <UButton :icon="panes.settings.value ? 'i-lucide-panel-right-close' : 'i-lucide-panel-right-open'" color="neutral" variant="ghost" size="sm" square class="ms-auto hidden lg:inline-flex rtl:-scale-x-100" :aria-label="panes.settings.value ? t('builder.pane.hideSettings') : t('builder.pane.showSettings')" :aria-pressed="panes.settings.value" @click="panes.settings.value = !panes.settings.value" />
    </UTooltip>
  </div>
</template>

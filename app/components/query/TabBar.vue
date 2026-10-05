<!--
  The Query editor's tabs (F12 M4): one per open statement. Click to switch, double-click the name
  to rename, × or a middle click to close, + for a new one; ← / → move between tabs. A running tab
  shows a spinner.
-->
<script setup lang="ts">
const props = defineProps<{ tabs: QueryTab[]; active: string; running: (id: string) => boolean; dirty: (tab: QueryTab) => boolean }>()
const emit = defineEmits<{ select: [id: string]; close: [id: string]; add: []; rename: [id: string, title: string] }>()
const { t } = useI18n()
const editing = ref<string | null>(null)
const draft = ref('')

function startRename(tab: QueryTab) {
  editing.value = tab.id
  draft.value = tab.title
  void nextTick(() => (document.getElementById(`query-tab-name-${tab.id}`) as HTMLInputElement | null)?.select())
}
function finishRename() {
  if (editing.value && draft.value.trim()) emit('rename', editing.value, draft.value.trim().slice(0, 40))
  editing.value = null
}
function onKey(event: KeyboardEvent, index: number) {
  const step = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0
  if (!step) return
  event.preventDefault()
  const rtl = getComputedStyle(event.target as Element).direction === 'rtl'
  const next = props.tabs[(index + step * (rtl ? -1 : 1) + props.tabs.length) % props.tabs.length]!
  emit('select', next.id)
  void nextTick(() => document.getElementById(`query-tab-${next.id}`)?.focus())
}
</script>

<template>
  <div class="flex min-w-0 items-end gap-1 overflow-x-auto border-b border-default px-2 pt-1.5" role="tablist" :aria-label="t('query.tabs')">
    <div
      v-for="(tab, index) in tabs"
      :key="tab.id"
      class="group flex max-w-52 shrink-0 items-center gap-1 rounded-t-md border border-b-0 ps-2.5 pe-1 text-xs"
      :class="tab.id === active ? 'border-default bg-default text-highlighted' : 'border-transparent text-muted hover:bg-elevated/60 hover:text-default'"
    >
      <UIcon v-if="running(tab.id)" name="i-lucide-loader-circle" class="size-3.5 shrink-0 animate-spin" />
      <UIcon v-else :name="tab.savedId ? 'i-lucide-bookmark' : 'i-lucide-square-terminal'" class="size-3.5 shrink-0 opacity-70" />
      <input
        v-if="editing === tab.id"
        :id="`query-tab-name-${tab.id}`"
        v-model="draft"
        class="h-7 w-28 bg-transparent outline-none"
        :aria-label="t('query.renameTab')"
        @keydown.enter.prevent="finishRename"
        @keydown.esc.prevent="editing = null"
        @blur="finishRename"
      >
      <button
        v-else
        :id="`query-tab-${tab.id}`"
        type="button"
        role="tab"
        :aria-selected="tab.id === active"
        :tabindex="tab.id === active ? 0 : -1"
        class="h-7 min-w-0 truncate focus-visible:outline-none focus-visible:underline"
        :title="t('query.tabHint')"
        @click="emit('select', tab.id)"
        @dblclick="startRename(tab)"
        @auxclick.prevent="(event: MouseEvent) => event.button === 1 && emit('close', tab.id)"
        @keydown="onKey($event, index)"
      >
        {{ tab.title }}
      </button>
      <span v-if="dirty(tab)" class="size-1.5 shrink-0 rounded-full bg-(--ui-text-highlighted)" :title="t('query.unsaved')" :aria-label="t('query.unsaved')" />
      <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" square class="size-5 rounded-sm p-0.5 opacity-60 group-hover:opacity-100" :aria-label="t('query.closeTab', { name: tab.title })" @click="emit('close', tab.id)" />
    </div>
    <UTooltip :text="t('query.newTab')">
      <UButton icon="i-lucide-plus" color="neutral" variant="ghost" size="xs" square class="mb-0.5" :aria-label="t('query.newTab')" @click="emit('add')" />
    </UTooltip>
  </div>
</template>

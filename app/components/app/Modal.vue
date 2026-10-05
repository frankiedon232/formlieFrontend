<!--
  The one modal wrapper for the portal: UModal + draggable header (mouse, touch, keyboard).
  Use instead of UModal so every dialog can be moved (CLAUDE.md rule 1).
-->
<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    /** false = no closing by outside click / Esc (e.g. unsaved changes). */
    dismissible?: boolean
    /** An outside click doesn't close it (forms people fill in, owner 2026-10-05); Esc, ✕ and Cancel still do. */
    keepOpen?: boolean
    ui?: Record<string, string>
  }>(),
  { description: undefined, dismissible: true, keepOpen: false, ui: undefined },
)

const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const { handle, enabled, reset, onKeydown } = useDraggableModal()

// Header: title block grows; the move grip and the close button sit side by side at the end, in
// the flow (Nuxt UI places the close button absolutely in the corner, where the grip overlapped it).
const ui = computed(() => ({ wrapper: 'flex-1 min-w-0', close: 'static shrink-0', ...props.ui }))
/** A clear close button: a soft round button, darker on hover. */
const closeButton = { color: 'neutral' as const, variant: 'soft' as const, size: 'sm' as const, square: true, class: 'rounded-full text-highlighted hover:bg-accented' }

const stay = (event: Event) => event.preventDefault()
const content = computed(() => (props.keepOpen ? { onPointerDownOutside: stay, onInteractOutside: stay } : undefined))

watch(open, value => {
  if (value) nextTick(reset)
})
</script>

<template>
  <UModal
    v-model:open="open"
    :title="props.title"
    :description="props.description"
    :dismissible="props.dismissible"
    :content="content"
    :close="closeButton"
    close-icon="i-lucide-x"
    :ui="ui"
  >
    <template v-if="$slots.title" #title>
      <slot name="title" />
    </template>
    <template v-if="$slots.description" #description>
      <slot name="description" />
    </template>

    <template #actions>
      <!-- Extra header buttons (e.g. reload / open in a new tab) before the move grip. -->
      <slot name="actions" />
      <span ref="handle" class="contents">
        <UTooltip v-if="enabled" :text="t('modal.moveHint')">
          <UButton
            data-drag-handle
            icon="i-lucide-grip"
            color="neutral"
            variant="ghost"
            size="sm"
            square
            class="cursor-grab text-muted active:cursor-grabbing"
            :aria-label="t('modal.move')"
            @keydown="onKeydown"
          />
        </UTooltip>
      </span>
    </template>

    <template v-if="$slots.close" #close="slotProps">
      <slot name="close" v-bind="slotProps" />
    </template>

    <template v-if="$slots.body" #body>
      <slot name="body" />
    </template>

    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </UModal>
</template>

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
    ui?: Record<string, string>
  }>(),
  { description: undefined, dismissible: true, ui: undefined },
)

const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const { handle, enabled, reset, onKeydown } = useDraggableModal()

// Title block grows so the grip sits next to the close button.
const ui = computed(() => ({ wrapper: 'flex-1 min-w-0', ...props.ui }))

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
    :ui="ui"
  >
    <template #actions>
      <span ref="handle" class="contents">
        <UTooltip v-if="enabled" :text="t('modal.moveHint')">
          <UButton
            data-drag-handle
            icon="i-lucide-grip"
            color="neutral"
            variant="ghost"
            :aria-label="t('modal.move')"
            @keydown="onKeydown"
          />
        </UTooltip>
      </span>
    </template>

    <template v-if="$slots.body" #body>
      <slot name="body" />
    </template>

    <template v-if="$slots.footer" #footer>
      <slot name="footer" />
    </template>
  </UModal>
</template>

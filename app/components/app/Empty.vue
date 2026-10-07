<!--
  The one empty / not-found / error state for the portal (owner 2026-10-05): evenly centred in the
  space it has, a layered icon tile (soft frame, solid card) inside a softly framed area with smooth corners, a clear title, a short muted
  description and the next step as buttons. Same props and slots as Nuxt UI's UEmpty, plus `tone`
  (error tints the icon). Use instead of UEmpty everywhere. The icon tile follows the workspace's
  Appearance colour (primary; black and white keeps it monochrome).
-->
<script setup lang="ts">
import type { ButtonProps } from '@nuxt/ui'

const props = withDefaults(
  defineProps<{
    icon?: string
    title?: string
    description?: string
    actions?: ButtonProps[]
    variant?: 'naked' | 'outline' | 'soft' | 'subtle' | 'solid'
    size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
    /** error / warning tint the icon; neutral otherwise (monochrome, as in the design). Unset: error icons tint themselves. */
    tone?: 'neutral' | 'error' | 'warning'
  }>(),
  {
    icon: 'i-lucide-inbox',
    title: undefined,
    description: undefined,
    actions: undefined,
    variant: 'naked',
    size: 'md',
    tone: undefined,
  },
)
const slots = useSlots()
const compact = computed(() => props.size === 'xs' || props.size === 'sm')
/** xs: inside a small panel or list (no minimum height). */
const tiny = computed(() => props.size === 'xs')
/** The free space it sits in: the frame stays compact and centred inside it. */
// A full page: the box sits a little above the middle (owner 2026-10-05), not dead centre.
const spaceClass = computed(() => (tiny.value ? 'py-1' : compact.value ? 'min-h-40 py-4' : 'min-h-64 pt-6 pb-[14vh]'))
const ui = computed(() => ({
  // A compact, softly framed card with smooth corners (owner 2026-10-05: not large)
  root: [
    'flex w-full flex-col items-center justify-center gap-0 text-center border border-default/60 bg-elevated/20',
    tiny.value
      ? 'max-w-60 rounded-xl px-3 py-3.5'
      : compact.value
        ? 'max-w-lg rounded-2xl px-8 py-9'
        : 'max-w-4xl rounded-2xl px-10 py-16',
  ].join(' '),
  header: 'flex flex-col items-center gap-0',
  title: tiny.value
    ? 'mt-2.5 text-xs font-semibold text-highlighted'
    : compact.value
      ? 'mt-4 text-sm font-semibold text-highlighted'
      : 'mt-5 text-base font-semibold text-highlighted',
  description: compact.value
    ? 'mt-1 max-w-xs text-xs text-pretty text-muted'
    : 'mt-1.5 max-w-sm text-sm text-pretty text-muted',
  body: tiny.value ? 'mt-3' : compact.value ? 'mt-4' : 'mt-5',
  actions: 'flex flex-wrap items-center justify-center gap-2',
}))
const ERROR_ICONS = /cloud-alert|plug-zap|circle-x|octagon-alert|server-crash|wifi-off|shield-alert/
const tone = computed(() => props.tone ?? (ERROR_ICONS.test(props.icon) ? 'error' : 'neutral'))
const toneClass = computed(
  () => ({ neutral: 'text-primary', error: 'text-error', warning: 'text-warning' })[tone.value],
)
const forwarded = computed(() => Object.keys(slots).filter(name => name !== 'leading'))
</script>

<template>
  <div class="flex w-full flex-1 items-center justify-center" :class="spaceClass">
    <UEmpty
      :title="title"
      :description="description"
      :actions="actions"
      :size="tiny ? 'xs' : compact ? 'sm' : 'md'"
      variant="naked"
      :ui="ui"
    >
      <template #leading>
        <slot name="leading">
          <!-- Layered tile: a soft frame around a solid card holding the icon -->
          <span
            class="relative flex items-center justify-center border border-primary/15 bg-primary/5"
            :class="tiny ? 'size-10 rounded-xl' : compact ? 'size-14 rounded-2xl' : 'size-18 rounded-2xl'"
            aria-hidden="true"
          >
            <span
              class="flex items-center justify-center border border-primary/25 bg-primary/10 shadow-sm"
              :class="tiny ? 'size-7 rounded-lg' : compact ? 'size-10 rounded-xl' : 'size-12 rounded-xl'"
            >
              <UIcon :name="icon" :class="[tiny ? 'size-4' : compact ? 'size-5' : 'size-6', toneClass]" />
            </span>
          </span>
        </slot>
      </template>
      <template v-for="name in forwarded" :key="name" #[name]="slotProps">
        <slot :name="name" v-bind="slotProps ?? {}" />
      </template>
    </UEmpty>
  </div>
</template>

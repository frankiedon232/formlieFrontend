<!--
  Help guide on the form (F10, owner 2026-10-03): a round "?" button floating in the bottom corner
  (the form's own colour) opens a chat-style panel, not a chat, with the creator's guide on how
  to fill in the form. Only when the creator turned it on and wrote one. Esc or the close button
  closes it; focus moves into the panel and back to the button.
-->
<script setup lang="ts">
const props = defineProps<{ title: string; html: string }>()
const { t } = useI18n()

const open = ref(false)
const panel = useTemplateRef<HTMLElement>('panel')
const button = useTemplateRef<{ $el: HTMLElement }>('button')
watch(open, async value => {
  await nextTick()
  if (value) panel.value?.focus()
  else button.value?.$el?.focus?.()
})
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && open.value) {
    event.stopPropagation()
    open.value = false
  }
}
const heading = computed(() => props.title.trim() || t('renderer.guide.defaultTitle'))
</script>

<template>
  <!-- Sticky to the bottom of the screen (or of a preview), above the form. -->
  <!-- Zero height: floats over the bottom corner without adding space under the footer. -->
  <div class="pointer-events-none sticky bottom-4 z-30 h-0 sm:bottom-6" @keydown="onKeydown">
    <div class="pointer-events-auto absolute end-4 bottom-0 flex flex-col items-end sm:end-6">
      <Transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="translate-y-2 scale-95 opacity-0"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="translate-y-2 scale-95 opacity-0"
      >
        <section
          v-if="open"
          id="form-guide-panel"
          ref="panel"
          tabindex="-1"
          role="dialog"
          :aria-label="heading"
          class="absolute end-0 bottom-16 flex max-h-[min(70dvh,34rem)] w-[min(24rem,calc(100vw-2rem))] origin-bottom-right flex-col overflow-hidden rounded-2xl border border-(--ui-border) bg-(--form-container-bg) shadow-2xl outline-none rtl:origin-bottom-left"
        >
          <header class="flex items-center gap-3 border-b border-(--ui-border) px-4 py-3" :style="{ background: 'color-mix(in oklab, var(--ui-primary) 8%, var(--form-container-bg))' }">
            <span class="flex size-8 shrink-0 items-center justify-center rounded-full bg-(--ui-primary) text-(--ui-text-inverted)">
              <UIcon name="i-lucide-life-buoy" class="size-4" />
            </span>
            <div class="flex min-w-0 flex-1 flex-col">
              <h2 class="truncate text-sm font-semibold text-(--ui-text-highlighted)">{{ heading }}</h2>
              <p class="truncate text-xs text-(--ui-text-muted)">{{ t('renderer.guide.subtitle') }}</p>
            </div>
            <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="sm" class="rounded-full" :aria-label="t('renderer.guide.close')" @click="open = false" />
          </header>
          <div class="min-h-0 flex-1 overflow-y-auto px-4 py-3 text-sm">
            <FormsRendererRichView :html="html" />
          </div>
        </section>
      </Transition>

      <UTooltip :text="open ? t('renderer.guide.close') : t('renderer.guide.open')">
        <UButton
          ref="button"
          :icon="open ? 'i-lucide-x' : 'i-lucide-circle-help'"
          color="primary"
          size="xl"
          class="size-12 justify-center rounded-full shadow-lg ring-4 ring-(--ui-primary)/15 transition hover:scale-105"
          :aria-label="open ? t('renderer.guide.close') : t('renderer.guide.open')"
          :aria-expanded="open"
          aria-controls="form-guide-panel"
          @click="open = !open"
        />
      </UTooltip>
    </div>
  </div>
</template>

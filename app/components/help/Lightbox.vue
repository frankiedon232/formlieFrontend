<!--
  The help centre's picture viewer (owner 2026-10-10): a screenshot opens over the page, never in a new tab.
  Close (✕ or Esc), zoom (buttons, + / - / 0, Ctrl + wheel, double-click), drag to move around a zoomed picture,
  and Previous / Next (arrows) when an article has several. Full screen, so it's a UModal of its own rather than
  the draggable AppModal (there is nothing to move). Right-click and dragging the picture out are off; the
  pictures carry Formalie's watermark.
-->
<script setup lang="ts">
const props = defineProps<{ images: { src: string; caption: string }[] }>()
const open = defineModel<boolean>('open', { default: false })
const index = defineModel<number>('index', { default: 0 })
const { t } = useI18n()

const STEPS = [1, 1.5, 2, 3, 4]
const zoom = ref(1)
const image = computed(() => props.images[index.value] ?? null)
watch([open, index], () => (zoom.value = 1))

const zoomIn = () => (zoom.value = STEPS.find(step => step > zoom.value) ?? zoom.value)
const zoomOut = () => (zoom.value = [...STEPS].reverse().find(step => step < zoom.value) ?? 1)
const reset = () => (zoom.value = 1)
const go = (step: number) => props.images.length > 1 && (index.value = (index.value + step + props.images.length) % props.images.length)

function onKeydown(event: KeyboardEvent) {
  if (event.key === '+' || event.key === '=') zoomIn()
  else if (event.key === '-') zoomOut()
  else if (event.key === '0') reset()
  else if (event.key === 'ArrowRight') go(document.dir === 'rtl' ? -1 : 1)
  else if (event.key === 'ArrowLeft') go(document.dir === 'rtl' ? 1 : -1)
  else return
  event.preventDefault()
}
function onWheel(event: WheelEvent) {
  if (!event.ctrlKey) return
  event.preventDefault()
  if (event.deltaY < 0) zoomIn()
  else zoomOut()
}

// Drag to move around a zoomed picture (the stage scrolls)
const stage = useTemplateRef<HTMLElement>('stage')
let drag: { x: number; y: number; left: number; top: number } | null = null
function onPointerDown(event: PointerEvent) {
  if (zoom.value === 1 || !stage.value) return
  drag = { x: event.clientX, y: event.clientY, left: stage.value.scrollLeft, top: stage.value.scrollTop }
  ;(event.target as HTMLElement).setPointerCapture?.(event.pointerId)
}
function onPointerMove(event: PointerEvent) {
  if (!drag || !stage.value) return
  stage.value.scrollLeft = drag.left - (event.clientX - drag.x)
  stage.value.scrollTop = drag.top - (event.clientY - drag.y)
}
const onPointerUp = () => (drag = null)
</script>

<template>
  <UModal v-model:open="open" fullscreen :title="image?.caption ?? t('help.viewer.title')" :ui="{ content: 'bg-neutral-950/95 text-white ring-0', header: 'hidden', body: 'flex min-h-0 flex-1 flex-col p-0 sm:p-0' }">
    <template #body>
      <div class="flex min-h-0 flex-1 flex-col" tabindex="-1" @keydown="onKeydown">
        <!-- Top bar: what it shows, zoom and close -->
        <div class="flex items-center gap-2 px-3 py-2 sm:px-4">
          <p class="min-w-0 flex-1 truncate text-sm text-white/80">
            <span v-if="images.length > 1" class="me-2 text-white/50 tabular-nums">{{ t('help.viewer.of', { n: index + 1, total: images.length }) }}</span>{{ image?.caption }}
          </p>
          <UTooltip :text="t('help.viewer.zoomOut')" :kbds="['-']">
            <UButton icon="i-lucide-zoom-out" color="neutral" variant="ghost" square class="text-white hover:bg-white/10" :disabled="zoom === 1" :aria-label="t('help.viewer.zoomOut')" @click="zoomOut" />
          </UTooltip>
          <UButton :label="`${Math.round(zoom * 100)}%`" color="neutral" variant="ghost" size="sm" class="w-14 justify-center text-white tabular-nums hover:bg-white/10" :aria-label="t('help.viewer.reset')" @click="reset" />
          <UTooltip :text="t('help.viewer.zoomIn')" :kbds="['+']">
            <UButton icon="i-lucide-zoom-in" color="neutral" variant="ghost" square class="text-white hover:bg-white/10" :disabled="zoom === STEPS.at(-1)" :aria-label="t('help.viewer.zoomIn')" @click="zoomIn" />
          </UTooltip>
          <UTooltip :text="t('help.viewer.close')" :kbds="['esc']">
            <UButton icon="i-lucide-x" color="neutral" variant="soft" square class="ms-1 rounded-full bg-white/10 text-white hover:bg-white/20" :aria-label="t('help.viewer.close')" autofocus @click="open = false" />
          </UTooltip>
        </div>

        <!-- The picture: fits the screen, zoomed it scrolls and can be dragged -->
        <div
          ref="stage"
          class="relative flex min-h-0 flex-1 overflow-auto"
          :class="zoom > 1 ? 'cursor-grab active:cursor-grabbing' : ''"
          @wheel="onWheel"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
          @pointercancel="onPointerUp"
        >
          <img
            v-if="image"
            :key="image.src"
            :src="image.src"
            :alt="image.caption"
            draggable="false"
            class="m-auto max-w-none rounded-md shadow-2xl select-none"
            :style="zoom === 1 ? { maxWidth: 'calc(100% - 2rem)', maxHeight: 'calc(100% - 2rem)' } : { width: `${zoom * 100}%`, maxWidth: 'none' }"
            @contextmenu.prevent
            @dblclick="zoom === 1 ? (zoom = 2) : reset()"
          >
          <template v-if="images.length > 1">
            <UButton icon="i-lucide-chevron-left" color="neutral" variant="soft" size="lg" square class="fixed start-3 top-1/2 -translate-y-1/2 rounded-full bg-white/10 text-white hover:bg-white/20 rtl:rotate-180" :aria-label="t('help.viewer.previous')" @click="go(-1)" />
            <UButton icon="i-lucide-chevron-right" color="neutral" variant="soft" size="lg" square class="fixed end-3 top-1/2 -translate-y-1/2 rounded-full bg-white/10 text-white hover:bg-white/20 rtl:rotate-180" :aria-label="t('help.viewer.next')" @click="go(1)" />
          </template>
        </div>
        <p class="px-4 py-2 text-center text-[11px] text-white/50">{{ t('help.viewer.hint') }}</p>
      </div>
    </template>
  </UModal>
</template>

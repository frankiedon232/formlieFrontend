<!--
  File / image upload (Nuxt UI file upload; real uploads go through pre-signed URLs, F9),
  signature (draw with mouse, pen or finger; keyboard users can type their name instead), payment (soon).
-->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()

const p = computed(() => (props.field.props ?? {}) as Record<string, number | string | undefined>)
// Read-only and disabled both block changes here (Nuxt UI choice controls have no read-only state).
const disabled = computed(() => isLocked(props.field))
const multiple = computed(() => Number(p.value.max_files ?? 1) > 1)
const files = ref<File[] | File | null>(null)
// Drag and drop skips the picker's `accept` filter, so check type and size here too.
const rejected = ref<string[]>([])
watch(files, next => {
  const list = next == null ? [] : Array.isArray(next) ? next : [next]
  const maxBytes = Number(p.value.max_mb ?? 10) * 1024 * 1024
  const ok = list.filter(file => acceptsFile(String(p.value.accept ?? ''), file) && file.size <= maxBytes)
  rejected.value = list.filter(file => !ok.includes(file)).map(file => file.name)
  if (ok.length !== list.length) {
    files.value = multiple.value ? ok : (ok[0] ?? null)
    return
  }
  value.value = next
})

// ── Signature ──────────────────────────────────────────────────────────────────────
const canvas = useTemplateRef<HTMLCanvasElement>('canvas')
const typed = ref('')
let drawing = false
function point(event: PointerEvent) {
  const rect = canvas.value!.getBoundingClientRect()
  return [event.clientX - rect.left, event.clientY - rect.top] as const
}
function down(event: PointerEvent) {
  if (disabled.value || !canvas.value) return
  drawing = true
  canvas.value.setPointerCapture(event.pointerId)
  const ctx = canvas.value.getContext('2d')!
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.strokeStyle = getComputedStyle(canvas.value).color
  ctx.beginPath()
  ctx.moveTo(...point(event))
}
function moveTo(event: PointerEvent) {
  if (!drawing || !canvas.value) return
  const ctx = canvas.value.getContext('2d')!
  ctx.lineTo(...point(event))
  ctx.stroke()
}
function up() {
  if (!drawing || !canvas.value) return
  drawing = false
  value.value = canvas.value.toDataURL('image/png')
}
function clear() {
  canvas.value?.getContext('2d')?.clearRect(0, 0, canvas.value.width, canvas.value.height)
  typed.value = ''
  value.value = null
}
watch(typed, name => {
  if (name) value.value = { typed: name }
})
</script>

<template>
  <div v-if="field.type === 'signature'" :id="id" class="flex flex-col gap-2">
    <div class="relative rounded-md border border-default bg-default">
      <canvas
        ref="canvas"
        width="600"
        height="160"
        class="h-36 w-full touch-none text-highlighted"
        :class="disabled ? '' : 'cursor-crosshair'"
        :aria-label="t('renderer.signHere')"
        role="img"
        @pointerdown="down"
        @pointermove="moveTo"
        @pointerup="up"
        @pointercancel="up"
      />
      <span
        class="pointer-events-none absolute inset-x-4 bottom-3 border-t border-dashed border-default pt-1 text-xs text-muted"
      >
        {{ t('renderer.signHere') }}
      </span>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <UInput
        v-model="typed"
        size="sm"
        :placeholder="t('renderer.typeName')"
        :disabled="disabled"
        class="min-w-0 flex-1"
      />
      <UButton
        :label="t('renderer.clear')"
        icon="i-lucide-eraser"
        color="neutral"
        variant="outline"
        size="sm"
        :disabled="disabled"
        @click="clear"
      />
    </div>
  </div>

  <div
    v-else-if="field.type === 'payment'"
    :id="id"
    class="flex items-center gap-2 rounded-md border border-dashed border-default px-3 py-4 text-sm text-muted"
  >
    <UIcon name="i-lucide-credit-card" class="size-4" />
    {{ t('renderer.paymentSoon') }}
  </div>

  <UFileUpload
    v-else
    :id="id"
    v-model="files"
    :multiple="multiple"
    :accept="String(p.accept || '') || undefined"
    :label="field.type === 'image_upload' ? t('renderer.dropImages') : t('renderer.dropFiles')"
    :description="t('renderer.fileLimit', { mb: p.max_mb ?? 10 })"
    :icon="field.type === 'image_upload' ? 'i-lucide-image-up' : 'i-lucide-upload'"
    color="neutral"
    layout="grid"
    position="outside"
    :disabled="disabled"
    :interactive="!disabled"
    :ui="{
      base: 'min-h-28',
      files: 'grid w-full grid-cols-3 gap-2 @sm:grid-cols-4 @lg:grid-cols-6',
      file: 'relative inset-auto aspect-square p-0',
    }"
    class="w-full"
  />
  <p v-if="rejected.length" class="text-xs text-error" role="alert">
    {{ t('renderer.fileRejected', { files: rejected.join(', '), mb: p.max_mb ?? 10 }) }}
  </p>
</template>

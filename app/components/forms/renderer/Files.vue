<!--
  File / image upload (Nuxt UI file upload; real uploads go through pre-signed URLs, F10),
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
const maxFiles = computed(() => Math.max(1, Number(p.value.max_files ?? 1)))
const maxMb = computed(() => Number(p.value.max_mb ?? 10))
const multiple = computed(() => maxFiles.value > 1)
const files = ref<File[] | File | null>(null)
const count = computed(() => (files.value == null ? 0 : Array.isArray(files.value) ? files.value.length : 1))
const toast = useToast()

/**
 * Every pick or drop is checked here (drag and drop skips the picker's `accept` filter): wrong
 * type, too big, or over the file limit is taken out again, said under the field and in a toast,
 * so nobody wonders why a file "didn't work".
 */
const rejected = ref<string[]>([])
let trimming = false
watch(files, next => {
  const list = next == null ? [] : Array.isArray(next) ? next : [next]
  const maxBytes = maxMb.value * 1024 * 1024
  const wrongType = list.filter(file => !acceptsFile(String(p.value.accept ?? ''), file))
  const tooBig = list.filter(file => !wrongType.includes(file) && file.size > maxBytes)
  const fitting = list.filter(file => !wrongType.includes(file) && !tooBig.includes(file))
  const kept = fitting.slice(0, maxFiles.value)
  const overLimit = fitting.slice(maxFiles.value)

  const problems: string[] = []
  if (wrongType.length) problems.push(t('renderer.files.wrongType', { files: wrongType.map(f => f.name).join(', ') }))
  if (tooBig.length) problems.push(t('renderer.files.tooBig', { files: tooBig.map(f => f.name).join(', '), mb: maxMb.value }))
  if (overLimit.length) problems.push(t('renderer.files.tooMany', { max: maxFiles.value, n: overLimit.length }, overLimit.length))
  if (problems.length) {
    rejected.value = problems
    for (const description of problems)
      toast.add({ title: t('renderer.files.notAdded'), description, color: 'warning', icon: 'i-lucide-file-x' })
    trimming = true
    files.value = multiple.value ? kept : (kept[0] ?? null)
    return
  }
  // The message under the field stays until the next pick that is fully fine.
  if (!trimming) rejected.value = []
  trimming = false
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
    :description="multiple ? t('renderer.files.limits', { max: maxFiles, mb: maxMb }) : t('renderer.fileLimit', { mb: maxMb })"
    :icon="field.type === 'image_upload' ? 'i-lucide-image-up' : 'i-lucide-upload'"
    color="neutral"
    layout="grid"
    position="inside"
    :disabled="disabled"
    :interactive="!disabled && count < maxFiles"
    :file-delete="{ color: 'neutral', variant: 'outline', size: 'xs', class: 'rounded-full bg-default shadow-sm text-highlighted' }"
    :ui="{
      base: 'min-h-28',
      // Thumbnails inside the zone (owner, 2026-10-03) — a single image must not cover the whole box
      // (Nuxt UI places a lone grid file `absolute inset-0`; `relative inset-auto` undoes that).
      files: 'flex w-full flex-wrap gap-2',
      file: 'relative inset-auto size-20 shrink-0 overflow-visible p-0 @sm:size-24',
      fileLeadingAvatar: 'size-full rounded-lg object-cover',
    }"
    class="w-full"
  >
    <!-- Inside the zone: how many of the allowed files, and "Add more" while there is room. -->
    <template #files-bottom="{ open }">
      <div v-if="count" class="flex w-full flex-wrap items-center justify-between gap-2 pt-1">
        <span class="text-xs text-muted tabular-nums">{{ t('renderer.files.count', { n: count, max: maxFiles }) }}</span>
        <UButton
          v-if="multiple && count < maxFiles && !disabled"
          :label="t('renderer.files.addMore')"
          icon="i-lucide-plus"
          color="neutral"
          variant="outline"
          size="xs"
          @click.stop="open()"
        />
      </div>
    </template>
  </UFileUpload>
  <ul v-if="rejected.length" class="flex flex-col gap-0.5 text-xs text-warning" role="alert">
    <li v-for="problem in rejected" :key="problem" class="flex items-start gap-1">
      <UIcon name="i-lucide-file-x" class="mt-0.5 size-3.5 shrink-0" />{{ problem }}
    </li>
  </ul>
</template>

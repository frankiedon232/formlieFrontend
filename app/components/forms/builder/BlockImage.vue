<!--
  Image block on the canvas.
  Empty: drop / browse an image (PNG, JPG, WebP, GIF, SVG · 5 MB, uploaded with progress) or paste
  a link. With an image: drag the handle on its edge to resize (or use ← → on the handle, 5 % steps;
  width chips 25 / 50 / 75 / 100), Replace / Remove on hover, and an inline prompt for alt text.
-->
<script setup lang="ts">
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ field: FormField; selected: boolean }>()
const { t } = useI18n()
const builder = useBuilder()
const toast = useToast()
const { handle } = useErrorHandler()
const { upload, progress, uploading, cancel } = useUpload()

const TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/svg+xml']
const MAX_MB = 5
const p = computed(() => (props.field.props ?? {}) as Record<string, unknown>)
const src = computed(() => (typeof p.value.src === 'string' ? p.value.src : ''))
const size = computed(() => Math.min(100, Math.max(10, Number(p.value.size ?? 100))))
const set = (patch: Record<string, unknown>, group?: string) => builder.updateProps(props.field.id, patch, group)

// ── Upload ──────────────────────────────────────────────────────────────────────────
const file = ref<File | null>(null)
const picker = useTemplateRef<HTMLInputElement>('picker')
async function take(picked: File | null | undefined) {
  if (!picked) return
  if (!TYPES.includes(picked.type))
    return toast.add({ title: t('builder.blocks.imageType'), color: 'error', icon: 'i-lucide-image-off' })
  if (picked.size > MAX_MB * 1024 * 1024)
    return toast.add({ title: t('builder.blocks.imageSize', { mb: MAX_MB }), color: 'error', icon: 'i-lucide-image-off' })
  try {
    const uploaded = await upload(picked, 'form_image')
    set({ src: uploaded.url, upload_id: uploaded.id, ...(p.value.alt ? {} : { alt: '' }) })
  } catch (error) {
    handle(error)
  } finally {
    file.value = null
  }
}
watch(file, picked => take(picked))

// ── Link ────────────────────────────────────────────────────────────────────────────
const link = ref('')
const linkError = computed(() => (link.value && !/^https:\/\/\S+$/i.test(link.value) ? t('builder.blocks.linkInvalid') : ''))
function useLink() {
  if (!link.value || linkError.value) return
  set({ src: link.value, upload_id: null })
  link.value = ''
}

// ── Resize (pointer drag on the handle, or arrow keys) ──────────────────────────────
const frame = useTemplateRef<HTMLElement>('frame')
const live = ref<number | null>(null)
const shown = computed(() => live.value ?? size.value)
const snap = (value: number) => Math.min(100, Math.max(10, Math.round(value / 5) * 5))
function startResize(event: PointerEvent) {
  const box = frame.value?.getBoundingClientRect()
  if (!box) return
  const target = event.currentTarget as HTMLElement
  target.setPointerCapture(event.pointerId)
  const rtl = getComputedStyle(target).direction === 'rtl'
  const centred = (p.value.align ?? 'center') === 'center'
  const move = (e: PointerEvent) => {
    const fromStart = rtl ? box.right - e.clientX : e.clientX - box.left
    const width = centred ? Math.abs(e.clientX - (box.left + box.width / 2)) * 2 : fromStart
    live.value = snap((width / box.width) * 100)
  }
  const up = () => {
    target.removeEventListener('pointermove', move)
    if (live.value !== null && live.value !== size.value) set({ size: live.value })
    live.value = null
  }
  target.addEventListener('pointermove', move)
  target.addEventListener('pointerup', up, { once: true })
}
function keyResize(event: KeyboardEvent) {
  const step = event.key === 'ArrowRight' || event.key === 'ArrowUp' ? 5 : event.key === 'ArrowLeft' || event.key === 'ArrowDown' ? -5 : 0
  if (!step) return
  event.preventDefault()
  const rtl = getComputedStyle(event.currentTarget as HTMLElement).direction === 'rtl'
  set({ size: snap(size.value + (rtl && (event.key === 'ArrowLeft' || event.key === 'ArrowRight') ? -step : step)) }, `image:${props.field.id}:size`)
}
const ALIGN: Record<string, string> = { start: 'items-start', center: 'items-center', end: 'items-end', fill: 'items-stretch' }
const fill = computed(() => p.value.align === 'fill')
const HEIGHT: Record<string, string> = { sm: 'h-40', md: 'h-60', lg: 'h-90' }
const banner = computed(() => (fill.value && HEIGHT[String(p.value.height ?? '')]) || '')
const width = computed(() => (fill.value ? '100%' : `${shown.value}%`))
</script>

<template>
  <!-- Empty: upload or link -->
  <div v-if="!src" class="flex flex-col gap-2" @click.stop>
    <UFileUpload
      v-model="file"
      :accept="TYPES.join(',')"
      :label="t('builder.blocks.imageDrop')"
      :description="t('builder.blocks.imageHint', { mb: MAX_MB })"
      icon="i-lucide-image-up"
      color="neutral"
      layout="list"
      :disabled="uploading"
      class="min-h-32 w-full"
    />
    <div v-if="uploading" class="flex items-center gap-2" aria-live="polite">
      <UProgress :model-value="progress" color="neutral" size="xs" class="flex-1" />
      <span class="w-10 text-end text-xs text-muted">{{ progress }}%</span>
      <UButton :label="t('common.cancel')" color="neutral" variant="ghost" size="xs" @click="cancel" />
    </div>
    <UFormField :error="linkError || undefined">
      <UInput
        v-model="link"
        type="url"
        icon="i-lucide-link"
        size="sm"
        :placeholder="t('builder.blocks.imageLink')"
        class="w-full"
        @keydown.enter.prevent="useLink"
      >
        <template #trailing>
          <UButton :label="t('builder.blocks.useLink')" color="neutral" variant="link" size="xs" :disabled="!link || !!linkError" @click="useLink" />
        </template>
      </UInput>
    </UFormField>
  </div>

  <!-- With an image -->
  <div v-else ref="frame" class="flex flex-col gap-2" :class="ALIGN[String(p.align ?? 'center')]">
    <div class="group/img relative max-w-full" :style="{ width }">
      <img
        :src="src"
        :alt="String(p.alt ?? '')"
        class="w-full"
        :class="[p.rounded === false ? '' : 'rounded-md', banner ? `${banner} object-cover` : 'h-auto object-contain']"
        draggable="false"
      >
      <span
        v-if="live !== null"
        class="absolute start-2 top-2 rounded-md bg-inverted px-1.5 py-0.5 text-xs text-inverted"
        aria-hidden="true"
      >{{ shown }}%</span>
      <div
        class="absolute end-2 top-2 flex gap-1 transition-opacity"
        :class="selected ? 'opacity-100' : 'opacity-0 group-hover/img:opacity-100 focus-within:opacity-100'"
        @click.stop
      >
        <UButton icon="i-lucide-replace" :label="t('builder.blocks.replace')" color="neutral" variant="outline" size="xs" class="bg-default" :loading="uploading" @click="picker?.click()" />
        <UButton icon="i-lucide-trash-2" color="neutral" variant="outline" size="xs" square class="bg-default" :aria-label="t('builder.blocks.removeImage')" @click="set({ src: '', upload_id: null })" />
      </div>
      <!-- Resize handle on the end edge (not for "Fill": it always spans the field) -->
      <button
        v-if="!fill"
        type="button"
        role="slider"
        :aria-label="t('builder.blocks.resize')"
        :aria-valuenow="shown"
        aria-valuemin="10"
        aria-valuemax="100"
        :aria-valuetext="`${shown}%`"
        class="absolute -end-1.5 top-1/2 h-10 w-3 -translate-y-1/2 cursor-ew-resize touch-none rounded-full border border-default bg-default shadow-sm transition-opacity focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :class="selected || live !== null ? 'opacity-100' : 'opacity-0 group-hover/img:opacity-100'"
        @pointerdown.stop.prevent="startResize"
        @click.stop
        @keydown="keyResize"
      />
      <UProgress v-if="uploading" :model-value="progress" color="neutral" size="xs" class="absolute inset-x-2 bottom-2" />
    </div>
    <input ref="picker" type="file" :accept="TYPES.join(',')" class="hidden" @change="take(($event.target as HTMLInputElement).files?.[0])">
    <p v-if="p.caption" class="text-xs text-muted" :style="{ width }">{{ p.caption }}</p>
    <UInput
      v-if="selected && !p.alt"
      size="sm"
      icon="i-lucide-accessibility"
      :placeholder="t('builder.blocks.altPrompt')"
      :aria-label="t('builder.inspector.alt')"
      class="w-full max-w-md"
      @click.stop
      @change="(e: Event) => set({ alt: (e.target as HTMLInputElement).value })"
    />
  </div>
</template>

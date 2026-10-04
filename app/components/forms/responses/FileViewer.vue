<!--
  File viewer (F11; owner 2026-10-04: like the preview, every previewable file shown, the others
  with a clear note and a download). A stage like the preview page: pictures fitted, PDFs in the
  browser's viewer, video and audio with their players, text as text. Files a browser can't show
  say so, with Download. Several files: arrows on the stage (← / →) and a sliding thumbnail strip.
  Each file is opened over a short-lived private link (POST /responses/:id/files).
-->
<script setup lang="ts">
const props = defineProps<{ responseId: string; field: string; files: { name?: string; size?: number; type?: string; sample?: boolean }[]; index: number }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ 'update:index': [index: number] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { fileSize } = useFormat()

interface Link { url: string; download_url: string; name: string; type: string; size: number; previewable: boolean; sample: boolean }
const link = ref<Link | null>(null)
const loading = ref(false)
const text = ref<string | null>(null)
async function load() {
  loading.value = true
  link.value = null
  text.value = null
  try {
    const { data } = await api.post<Link>(`/responses/${props.responseId}/files`, { field: props.field, index: props.index })
    link.value = data
    if (data.previewable && data.type.startsWith('text/')) text.value = (await (await fetch(data.url)).text()).slice(0, 200_000)
  } catch (error) {
    handle(error)
  } finally {
    loading.value = false
  }
}
watch(() => [props.index, open.value] as const, ([, isOpen]) => isOpen && void load(), { immediate: true })

const kind = computed(() => {
  const type = link.value?.type ?? ''
  if (!link.value?.previewable) return 'none'
  if (type.startsWith('image/')) return 'image'
  if (type === 'application/pdf') return 'pdf'
  if (type.startsWith('video/')) return 'video'
  if (type.startsWith('audio/')) return 'audio'
  return 'text'
})
const go = (by: -1 | 1) => {
  const next = props.index + by
  if (next >= 0 && next < props.files.length) emit('update:index', next)
}
defineShortcuts({
  arrowleft: { usingInput: false, handler: () => open.value && go(-1) },
  arrowright: { usingInput: false, handler: () => open.value && go(1) },
})
const current = computed(() => props.files[props.index])
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="current?.name ?? t('responses.files.title')"
    :description="[current?.type, fileSize(current?.size)].filter(Boolean).join(' · ')"
    :ui="{ overlay: 'z-[70]', content: 'sm:max-w-4xl z-[71]', body: 'flex flex-col gap-3' }"
  >
    <template #body>
      <!-- Stage (like the preview page) -->
      <div class="relative flex h-[60vh] min-h-72 items-center justify-center overflow-hidden rounded-lg bg-elevated/40 p-3">
        <USkeleton v-if="loading" class="size-full rounded-md" />
        <img v-else-if="kind === 'image'" :src="link!.url" :alt="link!.name" class="max-h-full max-w-full rounded-md object-contain shadow-sm">
        <iframe v-else-if="kind === 'pdf'" :src="link!.url" :title="link!.name" class="size-full rounded-md border border-default bg-white" />
        <video v-else-if="kind === 'video'" :src="link!.url" controls class="max-h-full max-w-full rounded-md bg-black" />
        <div v-else-if="kind === 'audio'" class="flex w-full max-w-md flex-col items-center gap-4 rounded-lg border border-default bg-default p-6">
          <span class="flex size-14 items-center justify-center rounded-full bg-elevated"><UIcon name="i-lucide-audio-lines" class="size-7 text-muted" /></span>
          <audio :src="link!.url" controls class="w-full" />
        </div>
        <pre v-else-if="kind === 'text'" class="size-full overflow-auto rounded-md border border-default bg-default p-4 text-xs whitespace-pre-wrap text-default">{{ text }}</pre>
        <div v-else-if="link" class="flex max-w-sm flex-col items-center gap-3 text-center">
          <span class="flex size-16 items-center justify-center rounded-2xl bg-default ring-1 ring-(--ui-border)"><UIcon name="i-lucide-file-question" class="size-8 text-muted" /></span>
          <h3 class="text-base font-semibold text-highlighted">{{ t('responses.files.noPreview') }}</h3>
          <p class="text-sm text-muted">{{ t('responses.files.noPreviewDesc') }}</p>
          <UButton :to="link.download_url" external download :label="t('responses.files.download')" icon="i-lucide-download" color="neutral" />
        </div>

        <!-- Arrows -->
        <template v-if="files.length > 1">
          <UButton icon="i-lucide-chevron-left" color="neutral" variant="outline" class="absolute start-3 top-1/2 -translate-y-1/2 rounded-full bg-default/90 shadow-sm rtl:rotate-180" :disabled="index === 0" :aria-label="t('responses.files.previous')" @click="go(-1)" />
          <UButton icon="i-lucide-chevron-right" color="neutral" variant="outline" class="absolute end-3 top-1/2 -translate-y-1/2 rounded-full bg-default/90 shadow-sm rtl:rotate-180" :disabled="index === files.length - 1" :aria-label="t('responses.files.next')" @click="go(1)" />
        </template>
      </div>

      <!-- Bar: sample note, position, actions -->
      <div class="flex flex-wrap items-center gap-2">
        <UBadge v-if="link?.sample" :label="t('responses.files.sampleNote')" icon="i-lucide-info" color="neutral" variant="soft" class="rounded-md" />
        <span v-if="files.length > 1" class="text-xs text-muted tabular-nums">{{ t('responses.detail.position', { n: index + 1, total: files.length }) }}</span>
        <div class="ms-auto flex items-center gap-2">
          <UButton v-if="link?.previewable" :to="link.url" external target="_blank" :label="t('responses.files.newTab')" icon="i-lucide-external-link" color="neutral" variant="outline" size="sm" :ui="{ label: 'hidden sm:inline' }" />
          <UButton v-if="link" :to="link.download_url" external download :label="t('responses.files.download')" icon="i-lucide-download" color="neutral" size="sm" />
        </div>
      </div>

      <!-- Thumbnails: a sliding strip -->
      <div v-if="files.length > 1" class="-mx-1 flex snap-x gap-2 overflow-x-auto px-1 pb-1">
        <button
          v-for="(file, i) in files"
          :key="i"
          type="button"
          class="flex w-40 shrink-0 snap-start items-center gap-2 rounded-md border px-2.5 py-2 text-start text-xs transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          :class="i === index ? 'border-inverted bg-elevated' : 'border-default hover:bg-elevated/60'"
          :aria-current="i === index || undefined"
          @click="emit('update:index', i)"
        >
          <UIcon :name="file.type?.startsWith('image/') ? 'i-lucide-image' : 'i-lucide-file'" class="size-4 shrink-0 text-muted" />
          <span class="truncate text-default">{{ file.name }}</span>
        </button>
      </div>
    </template>
  </AppModal>
</template>

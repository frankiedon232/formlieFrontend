<!--
  The files of one answer (F11): a sliding strip of tiles, pictures as real thumbnails (loaded over
  short-lived private links), other files as a type badge with name and size. A tile opens the
  viewer at that file.
-->
<script setup lang="ts">
const props = defineProps<{ responseId: string; field: string; files: { name?: string; size?: number; type?: string; sample?: boolean }[] }>()
const { t } = useI18n()
const api = useApi()
const { fileSize } = useFormat()

const thumbs = ref<Record<number, string>>({})
watch(
  () => [props.responseId, props.field] as const,
  async () => {
    thumbs.value = {}
    await Promise.all(
      props.files.map(async (file, index) => {
        if (!file.type?.startsWith('image/')) return
        try {
          const { data } = await api.post<{ url: string; previewable: boolean }>(`/responses/${props.responseId}/files`, { field: props.field, index }, { background: true })
          if (data.previewable) thumbs.value = { ...thumbs.value, [index]: data.url }
        } catch {
          // The tile shows its icon instead.
        }
      }),
    )
  },
  { immediate: true },
)
const ext = (name = '') => (name.match(/\.([a-z0-9]+)$/i)?.[1] ?? 'file').toUpperCase()
const viewing = ref<number | null>(null)
const viewerUsed = ref(false)
function view(index: number) {
  viewing.value = index
  viewerUsed.value = true
}
</script>

<template>
  <div class="-mx-1 flex snap-x gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]">
    <button
      v-for="(file, index) in files"
      :key="index"
      type="button"
      class="group flex w-36 shrink-0 snap-start flex-col overflow-hidden rounded-lg border border-default bg-default text-start transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
      :aria-label="t('responses.files.open', { name: file.name })"
      @click="view(index)"
    >
      <span class="relative flex h-24 items-center justify-center overflow-hidden bg-elevated/60">
        <img v-if="thumbs[index]" :src="thumbs[index]" :alt="file.name" class="size-full object-cover transition-transform group-hover:scale-105" loading="lazy">
        <span v-else class="flex flex-col items-center gap-1 text-muted">
          <UIcon :name="file.type?.startsWith('image/') ? 'i-lucide-image' : file.type === 'application/pdf' ? 'i-lucide-file-text' : file.type?.startsWith('video/') ? 'i-lucide-file-video' : file.type?.startsWith('audio/') ? 'i-lucide-file-audio' : 'i-lucide-file'" class="size-7" />
          <span class="rounded bg-default px-1.5 py-px text-[10px] font-semibold tracking-wide text-toned ring-1 ring-(--ui-border)">{{ ext(file.name) }}</span>
        </span>
        <UBadge v-if="file.sample" :label="t('responses.detail.sampleFile')" color="neutral" variant="solid" size="sm" class="absolute start-1.5 top-1.5 rounded-md" />
      </span>
      <span class="flex flex-col px-2.5 py-2">
        <span class="truncate text-xs font-medium text-highlighted">{{ file.name }}</span>
        <span class="text-[11px] text-muted">{{ fileSize(file.size) }}</span>
      </span>
    </button>
  </div>
  <LazyFormsResponsesFileViewer v-if="viewerUsed" :response-id="responseId" :field="field" :files="files" :index="viewing ?? 0" :open="viewing !== null" @update:open="v => !v && (viewing = null)" @update:index="i => (viewing = i)" />
</template>

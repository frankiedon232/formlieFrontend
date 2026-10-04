<!--
  File and image questions (F10 M2). Each picked file is checked (type, size, how many), then goes
  straight to storage through a short-lived upload link with its own progress on the thumbnail; the
  answer keeps only a reference per file (FileAnswer). Next / Submit wait while uploads run
  (RENDERER_UPLOADS.pending). The preview has no uploader: files stay in the browser.
  Answers brought back by Save and resume show as tiles again (with the picture while this tab has it).
-->
<script setup lang="ts">
import { isLocked, type FormField } from '#shared/utils/forms/build'
import { fileAnswers, maxFileBytes } from '#shared/utils/forms/file-answers'
import { FILE_GROUP_ICONS, FILE_TYPE_GROUPS, type FileTypeGroup } from '#shared/utils/forms/file-types'
import type { FileAnswer } from '#shared/types/public'

const props = defineProps<{ id: string; field: FormField; mode: 'builder' | 'live' }>()
const value = defineModel<unknown>()
const { t } = useI18n()
const toast = useToast()
const uploads = inject(RENDERER_UPLOADS, null)

const p = computed(() => (props.field.props ?? {}) as Record<string, number | string | undefined>)
// Read-only and disabled both block changes here.
const disabled = computed(() => isLocked(props.field))
const maxFiles = computed(() => Math.max(1, Number(p.value.max_files ?? 1)))
const maxBytes = computed(() => maxFileBytes(p.value))
const maxMb = computed(() => Math.round(maxBytes.value / 1024 / 1024))
const multiple = computed(() => maxFiles.value > 1)
const image = computed(() => props.field.type === 'image_upload')
const accept = computed(() => String(p.value.accept || '') || (image.value ? 'image/*' : ''))

const files = ref<File[] | File | null>(null)
const listOf = (model: File[] | File | null) => (model == null ? [] : Array.isArray(model) ? model : [model])
const count = computed(() => listOf(files.value).length)

// ── Upload state per file ──────────────────────────────────────────────────────────────
interface Entry {
  status: 'uploading' | 'done'
  progress: number
  answer: FileAnswer | null
  preview: string | null
  abort?: () => void
}
const entries = reactive(new Map<File, Entry>())
const entry = (file: File) => entries.get(file)
const uploading = computed(() => [...entries.values()].filter(item => item.status === 'uploading').length)
const keyOf = (answer: FileAnswer) => answer.id || `${answer.name}:${answer.size}`
const pictureOf = (file: File) => (file.size && file.type.startsWith('image/') ? URL.createObjectURL(file) : null)

let synced = 'null'
/** The answer: every finished file, in the order shown. */
function sync() {
  const answers = listOf(files.value)
    .map(file => entries.get(file))
    .filter(item => item?.status === 'done' && item.answer)
    .map(item => item!.answer!)
  const next = answers.length ? answers : null
  synced = JSON.stringify(next)
  value.value = next
}

async function start(file: File) {
  entries.set(file, { status: 'uploading', progress: 0, answer: null, preview: pictureOf(file) })
  const current = entries.get(file)!
  if (props.mode !== 'live' || !uploads?.upload) {
    Object.assign(current, { status: 'done', progress: 100, answer: { id: '', name: file.name, size: file.size, type: file.type } })
    return
  }
  uploads.pending.value += 1
  try {
    const answer = await uploads.upload(props.field.key, file, percent => (current.progress = percent), abort => (current.abort = abort))
    if (entries.get(file) !== current) return // Removed while it was uploading.
    Object.assign(current, { status: 'done', progress: 100, answer, abort: undefined })
    if (current.preview) previews.set(keyOf(answer), current.preview)
  } catch (error) {
    if (entries.get(file) !== current) return
    const reason = (error as { message?: string }).message ?? ''
    const problem = t('renderer.files.failed', { file: file.name })
    rejected.value = [...rejected.value, problem]
    toast.add({ title: t('renderer.files.notAdded'), description: reason ? `${problem} ${reason}` : problem, color: 'error', icon: 'i-lucide-cloud-alert' })
    entries.delete(file)
    trimming = true
    const kept = listOf(files.value).filter(item => item !== file)
    files.value = multiple.value ? kept : (kept[0] ?? null)
  } finally {
    uploads.pending.value -= 1
    sync()
  }
}

/** Files taken out (or replaced): cancel their uploads; new files: start theirs. */
function reconcile(list: File[]) {
  for (const [file, item] of entries)
    if (!list.includes(file)) {
      item.abort?.()
      entries.delete(file)
    }
  for (const file of list) if (!entries.has(file)) void start(file)
  sync()
}

/**
 * Every pick or drop is checked here (drag and drop skips the picker's `accept` filter): wrong
 * type, too big, or over the file limit is taken out again, said under the field and in a toast.
 * The server checks the same again.
 */
const rejected = ref<string[]>([])
let trimming = false
watch(files, next => {
  const list = listOf(next)
  const wrongType = list.filter(file => !acceptsFile(accept.value, file))
  const tooBig = list.filter(file => !wrongType.includes(file) && file.size > maxBytes.value)
  const fitting = list.filter(file => !wrongType.includes(file) && !tooBig.includes(file))
  const kept = fitting.slice(0, maxFiles.value)
  const overLimit = fitting.slice(maxFiles.value)

  const problems: string[] = []
  if (wrongType.length) problems.push(t('renderer.files.wrongType', { files: wrongType.map(f => f.name).join(', ') }))
  if (tooBig.length) problems.push(t('renderer.files.tooBig', { files: tooBig.map(f => f.name).join(', '), mb: maxMb.value }))
  if (overLimit.length) problems.push(t('renderer.files.tooMany', { max: maxFiles.value, n: overLimit.length }, overLimit.length))
  if (problems.length) {
    rejected.value = problems
    for (const description of problems) toast.add({ title: t('renderer.files.notAdded'), description, color: 'warning', icon: 'i-lucide-file-x' })
    trimming = true
    files.value = multiple.value ? kept : (kept[0] ?? null)
    return
  }
  // The message under the field stays until the next pick that is fully fine.
  if (!trimming) rejected.value = []
  trimming = false
  reconcile(list)
})

// Answers set from outside (Save and resume, a restart, coming back to this page) become tiles again.
watch(
  value,
  next => {
    if (JSON.stringify(next ?? null) === synced) return
    const restored = fileAnswers(next)
    const stubs = restored.map(answer => {
      const stub = new File([], answer.name, { type: answer.type })
      entries.set(stub, { status: 'done', progress: 100, answer, preview: previews.get(keyOf(answer)) ?? null })
      return stub
    })
    synced = JSON.stringify(restored.length ? restored : null)
    files.value = multiple.value ? stubs : (stubs[0] ?? null)
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  for (const item of entries.values()) item.abort?.()
})

const sizeOf = (file: File) => entry(file)?.answer?.size ?? file.size
const iconOf = (file: File) => {
  const extension = file.name.toLowerCase().match(/\.[a-z0-9]+$/)?.[0] ?? ''
  const group = (Object.keys(FILE_TYPE_GROUPS) as FileTypeGroup[]).find(name => (FILE_TYPE_GROUPS[name] as readonly string[]).includes(extension))
  return group ? FILE_GROUP_ICONS[group] : 'i-lucide-file'
}
const { fileSize } = useFormat()
</script>

<script lang="ts">
/** Pictures picked in this tab, by answer, so tiles keep their picture when a page is shown again. */
const previews = new Map<string, string>()
</script>

<template>
  <UFileUpload
    :id="id"
    v-model="files"
    :multiple="multiple"
    :accept="accept || undefined"
    :label="image ? t('renderer.dropImages') : t('renderer.dropFiles')"
    :description="multiple ? t('renderer.files.limits', { max: maxFiles, mb: maxMb }) : t('renderer.fileLimit', { mb: maxMb })"
    :icon="image ? 'i-lucide-image-up' : 'i-lucide-upload'"
    color="neutral"
    layout="grid"
    position="inside"
    :disabled="disabled"
    :interactive="!disabled && count < maxFiles"
    :file-delete="{ color: 'neutral', variant: 'outline', size: 'xs', class: 'rounded-full bg-default shadow-sm text-highlighted' }"
    :ui="{
      base: 'min-h-28',
      // Thumbnails inside the zone (owner, 2026-10-03) — a single file must not cover the whole box
      // (Nuxt UI places a lone grid file `absolute inset-0`; `relative inset-auto` undoes that).
      files: 'flex w-full flex-wrap gap-2',
      file: 'relative inset-auto size-20 shrink-0 overflow-visible p-0 @sm:size-24',
    }"
    class="w-full"
  >
    <template #file-leading="{ file }">
      <div class="relative size-full overflow-hidden rounded-lg border border-default bg-elevated" :title="`${file.name} · ${fileSize(sizeOf(file))}`">
        <img v-if="entry(file)?.preview" :src="entry(file)!.preview!" alt="" class="size-full object-cover">
        <div v-else class="flex size-full flex-col items-center justify-center gap-1 p-1.5">
          <UIcon :name="iconOf(file)" class="size-6 shrink-0 text-muted" />
          <span class="w-full truncate text-center text-[10px] leading-tight text-toned">{{ file.name }}</span>
        </div>
        <span class="sr-only">{{ file.name }}, {{ fileSize(sizeOf(file)) }}</span>
        <!-- Progress of this file's upload; the remove button cancels it. -->
        <div
          v-if="entry(file)?.status === 'uploading'"
          class="absolute inset-0 flex flex-col items-center justify-center gap-1.5 bg-default/80 px-2"
          role="progressbar"
          :aria-label="t('renderer.files.uploadingFile', { file: file.name })"
          :aria-valuenow="entry(file)!.progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <span class="text-xs font-semibold tabular-nums text-highlighted">{{ entry(file)!.progress }}%</span>
          <UProgress :model-value="entry(file)!.progress" color="neutral" size="xs" class="w-full" />
        </div>
      </div>
    </template>

    <!-- Inside the zone: upload status or how many of the allowed files, and "Add more" while there is room. -->
    <template #files-bottom="{ open }">
      <div v-if="count" class="flex w-full flex-wrap items-center justify-between gap-2 pt-1">
        <span v-if="uploading" class="flex items-center gap-1.5 text-xs text-toned" role="status" aria-live="polite">
          <UIcon name="i-lucide-loader-circle" class="size-3.5 animate-spin" />
          {{ t('renderer.files.uploading', { n: uploading }, uploading) }}
        </span>
        <span v-else class="text-xs text-muted tabular-nums">{{ t('renderer.files.count', { n: count, max: maxFiles }) }}</span>
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

<!--
  Export the audit trail with the page's current search, filters and date range:
  choose a format → background job with progress → one-time download link.
-->
<script setup lang="ts">
import type { ExportFormat, ExportJob } from '#shared/types/audit'

const props = defineProps<{ filters: Record<string, string>; filterCount: number }>()
const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { busy, run } = useBusy()
const { number, relative } = useFormat()

const format = ref<ExportFormat>('xlsx')
const job = ref<ExportJob | null>(null)
const polling = ref(false)
let timer: ReturnType<typeof setTimeout> | null = null

const formats = computed(() => [
  { value: 'xlsx', label: t('audit.export.xlsx'), description: t('audit.export.xlsxDesc') },
  { value: 'csv', label: t('audit.export.csv'), description: t('audit.export.csvDesc') },
])

function stop() {
  if (timer) clearTimeout(timer)
  timer = null
  polling.value = false
}

async function poll(id: string) {
  try {
    const { data } = await api.get<ExportJob>(`/exports/${id}`, undefined, { background: true })
    job.value = data
    if (data.status === 'queued' || data.status === 'running') {
      timer = setTimeout(() => poll(id), 700)
      return
    }
    stop()
  } catch (error) {
    stop()
    job.value = null
    handle(error)
  }
}

async function start() {
  const created = await run(() =>
    api.post<ExportJob>('/audit-logs/export', { format: format.value, filters: props.filters }),
  )
  if (!created) return
  job.value = created.data
  polling.value = true
  poll(created.data.id)
}

watch(open, value => {
  if (!value) {
    stop()
    job.value = null
  }
})
onBeforeUnmount(stop)

const running = computed(() => polling.value || busy.value)
const ready = computed(() => job.value?.status === 'done' && !!job.value.download_url)
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('audit.export.title')"
    :description="t('audit.export.desc')"
    :dismissible="!running"
  >
    <template #body>
      <div v-if="!job" class="flex flex-col gap-4">
        <UFormField :label="t('audit.export.format')">
          <URadioGroup v-model="format" :items="formats" variant="card" color="neutral" class="w-full" />
        </UFormField>
        <p class="flex items-center gap-2 text-sm text-muted">
          <UIcon name="i-lucide-list-filter" class="size-4 shrink-0" />
          {{
            props.filterCount
              ? t('audit.export.applied', { count: props.filterCount }, props.filterCount)
              : t('audit.export.none')
          }}
        </p>
      </div>

      <div v-else-if="!ready" class="flex flex-col gap-3" aria-live="polite">
        <p class="text-sm text-highlighted">{{ t('audit.export.preparing') }}</p>
        <UProgress :model-value="job.progress" color="neutral" />
        <p class="text-xs text-muted">
          {{ t('audit.export.rows', { n: number(job.rows) }, job.rows) }} · {{ job.progress }}%
        </p>
      </div>

      <div v-else class="flex flex-col items-center gap-2 py-2 text-center" aria-live="polite">
        <UIcon name="i-lucide-circle-check" class="size-10 text-success" />
        <p class="font-medium text-highlighted">{{ t('audit.export.ready') }}</p>
        <p class="text-sm text-muted">
          {{ job.file_name }} · {{ t('audit.export.rows', { n: number(job.rows) }, job.rows) }}
        </p>
        <p class="text-xs text-muted">{{ t('audit.export.expires', { time: relative(job.expires_at) }) }}</p>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton
          :label="ready ? t('common.close') : t('common.cancel')"
          color="neutral"
          variant="outline"
          class="justify-center"
          :disabled="running"
          @click="open = false"
        />
        <UButton
          v-if="!job"
          :label="t('audit.export.start')"
          icon="i-lucide-file-down"
          color="neutral"
          class="justify-center"
          :loading="busy"
          @click="start"
        />
        <UButton
          v-else-if="ready"
          :label="t('audit.export.download')"
          icon="i-lucide-download"
          color="neutral"
          class="justify-center"
          :href="job.download_url!"
          :download="job.file_name"
          external
          @click="open = false"
        />
        <UButton v-else :label="t('audit.export.preparing')" color="neutral" class="justify-center" loading />
      </div>
    </template>
  </AppModal>
</template>

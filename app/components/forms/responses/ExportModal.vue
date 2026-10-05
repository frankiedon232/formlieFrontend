<!--
  Export responses (F11 M3): choose the format (Excel · CSV · PDF), which responses (all, those
  matching the list's filters, or the selected ones), the columns (the table's or every question)
  and whether to add review details; then the file is made with a progress bar and downloaded over
  a one-time private link. It stays 7 days on Responses → Exports.
-->
<script setup lang="ts">
import type { ResponseExport, ResponseExportFormat, ResponseExportScope } from '#shared/types/responses'

const props = defineProps<{
  formId: string
  /** The list's search, sort, date range and filters (API params). */
  query: Record<string, string | number>
  total: number
  filtered: number
  selectedIds: string[]
  /** Question keys shown in the table, in order. */
  columns: string[]
}>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { busy, run } = useBusy()
const { number, relative, fileSize } = useFormat()

const format = ref<ResponseExportFormat>('xlsx')
const scope = ref<ResponseExportScope>('all')
const allQuestions = ref(false)
const details = ref(true)
const job = ref<ResponseExport | null>(null)
let timer: ReturnType<typeof setTimeout> | null = null
const stop = () => (timer && clearTimeout(timer), (timer = null))

const hasFilters = computed(() => Object.keys(props.query).some(key => key !== 'sort'))
watch(open, value => {
  if (!value) return stop()
  job.value = null
  scope.value = props.selectedIds.length ? 'selected' : hasFilters.value ? 'filtered' : 'all'
})
onBeforeUnmount(stop)

const formats = computed(() => (['xlsx', 'csv', 'pdf'] as const).map(value => ({ value, label: t(`responses.export.format.${value}`), description: t(`responses.export.formatDesc.${value}`) })))
const scopes = computed(() => [
  { value: 'all', label: t('responses.export.scope.all', { n: number(props.total) }, props.total) },
  ...(hasFilters.value ? [{ value: 'filtered', label: t('responses.export.scope.filtered', { n: number(props.filtered) }, props.filtered) }] : []),
  ...(props.selectedIds.length ? [{ value: 'selected', label: t('responses.export.scope.selected', { n: number(props.selectedIds.length) }, props.selectedIds.length) }] : []),
])

async function poll(id: string) {
  try {
    const { data } = await api.get<ResponseExport>(`/responses/exports/${id}`, undefined, { background: true })
    job.value = data
    if (data.status === 'queued' || data.status === 'running') timer = setTimeout(() => poll(id), 600)
  } catch (error) {
    job.value = null
    handle(error)
  }
}
async function start() {
  const created = await run(() =>
    api.post<ResponseExport>(`/forms/${props.formId}/responses/export`, {
      format: format.value,
      scope: scope.value,
      query: scope.value === 'filtered' ? props.query : {},
      ids: scope.value === 'selected' ? props.selectedIds : [],
      columns: allQuestions.value ? [] : props.columns,
      details: details.value,
    }),
  )
  if (!created) return
  job.value = created.data
  void poll(created.data.id)
}
const downloading = useBusy()
async function download() {
  if (!job.value) return
  const id = job.value.id
  const link = await downloading.run(() => api.post<{ url: string }>(`/responses/exports/${id}/link`))
  if (link) window.location.assign(link.data.url)
}
const working = computed(() => !!job.value && (job.value.status === 'queued' || job.value.status === 'running'))
</script>

<template>
  <AppModal v-model:open="open" :title="t('responses.export.title')" :description="t('responses.export.desc')" :dismissible="!busy && !working" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div v-if="!job" class="flex flex-col gap-5">
        <UFormField :label="t('responses.export.formatLabel')">
          <URadioGroup v-model="format" :items="formats" variant="card" color="neutral" class="w-full" />
        </UFormField>
        <UFormField :label="t('responses.export.which')">
          <URadioGroup v-model="scope" :items="scopes" color="neutral" />
        </UFormField>
        <div class="flex flex-col gap-3 border-t border-default pt-4">
          <USwitch v-model="allQuestions" color="neutral" :label="t('responses.export.allQuestions')" :description="allQuestions ? t('responses.export.allQuestionsOn') : t('responses.export.allQuestionsOff', { n: columns.length }, columns.length)" />
          <USwitch v-model="details" color="neutral" :label="t('responses.export.details')" :description="t('responses.export.detailsHint')" />
        </div>
      </div>

      <div v-else-if="working" class="flex flex-col gap-3 py-2" aria-live="polite">
        <p class="text-sm font-medium text-highlighted">{{ t('responses.export.making') }}</p>
        <UProgress :model-value="job.progress" color="neutral" />
        <p class="text-xs text-muted tabular-nums">{{ t('responses.export.rows', { n: number(job.rows) }, job.rows) }} · {{ job.progress }}%</p>
      </div>

      <div v-else class="flex flex-col items-center gap-2 py-2 text-center" aria-live="polite">
        <UIcon name="i-lucide-circle-check" class="size-10 text-success" />
        <p class="font-medium text-highlighted">{{ t('responses.export.ready') }}</p>
        <p class="text-sm break-all text-muted">{{ job.file_name }} · {{ t('responses.export.rows', { n: number(job.rows) }, job.rows) }}<template v-if="job.size"> · {{ fileSize(job.size) }}</template></p>
        <p class="text-xs text-muted">{{ t('responses.export.kept', { when: relative(job.expires_at) }) }}</p>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-wrap items-center justify-end gap-2">
        <template v-if="!job">
          <UButton :label="t('common.cancel')" color="neutral" variant="outline" :disabled="busy" @click="open = false" />
          <UButton :label="t('responses.export.start')" icon="i-lucide-file-down" color="neutral" :loading="busy" @click="start" />
        </template>
        <template v-else-if="!working">
          <UButton :label="t('responses.export.allExports')" icon="i-lucide-list" color="neutral" variant="link" to="/responses/exports" class="me-auto" @click="open = false" />
          <UButton :label="t('common.close')" color="neutral" variant="outline" @click="open = false" />
          <UButton :label="t('responses.export.download')" icon="i-lucide-download" color="neutral" :loading="downloading.busy.value" @click="download" />
        </template>
      </div>
    </template>
  </AppModal>
</template>

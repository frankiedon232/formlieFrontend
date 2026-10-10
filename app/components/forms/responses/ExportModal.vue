<!--
  Export responses (F11 M3): choose the format (Excel · CSV · PDF), which responses (all, those
  matching the list's filters, or the selected ones), the columns (the table's or every question)
  and whether to add review details; then the file is made with a progress bar and downloaded over
  a one-time private link. It stays 7 days on Responses → Exports.
  Without `formId` (Exports page "New export", owner 2026-10-05) it first asks which form, with search.
  Once Export is pressed (preparing, progress, ready) it only closes with Close or ✕, never by a
  click outside or Esc, so nobody thinks the export failed (owner 2026-10-05).
-->
<script setup lang="ts">
import type { ResponseExport, ResponseExportFormat, ResponseExportScope, ResponseFormRow } from '#shared/types/responses'

const props = withDefaults(
  defineProps<{
    /** The form to export; none = pick one in the dialog. */
    formId?: string | null
    /** The list's search, sort, date range and filters (API params). */
    query?: Record<string, string | number>
    total?: number
    filtered?: number
    selectedIds?: string[]
    /** Question keys shown in the table, in order (none = every question). */
    columns?: string[]
  }>(),
  { formId: null, query: () => ({}), total: 0, filtered: 0, selectedIds: () => [], columns: () => [] },
)
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ created: [] }>()
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

// Which form: given by the page, or picked here (forms with responses, searchable).
const forms = ref<ResponseFormRow[]>([])
const formsLoading = ref(false)
const pickedId = ref<string | undefined>()
async function loadForms() {
  formsLoading.value = true
  try {
    forms.value = (await api.list<ResponseFormRow>('/responses/forms', { page_size: 100, sort: 'name' }, { background: true })).data
  } catch (error) {
    handle(error)
  } finally {
    formsLoading.value = false
  }
}
const formItems = computed(() => forms.value.filter(form => form.can?.export !== false).map(form => ({ label: form.name, value: form.id, description: t('responses.export.rows', { n: number(form.total) }, form.total) })))
const formId = computed(() => props.formId ?? pickedId.value ?? null)
const total = computed(() => (props.formId ? props.total : (forms.value.find(form => form.id === pickedId.value)?.total ?? 0)))

const hasFilters = computed(() => Object.keys(props.query).some(key => key !== 'sort'))
watch(open, value => {
  if (!value) return stop()
  job.value = null
  scope.value = props.selectedIds.length ? 'selected' : hasFilters.value ? 'filtered' : 'all'
  if (!props.formId) {
    pickedId.value = undefined
    void loadForms()
  }
})
onBeforeUnmount(stop)

const formats = computed(() => (['xlsx', 'csv', 'pdf'] as const).map(value => ({ value, label: t(`responses.export.format.${value}`), description: t(`responses.export.formatDesc.${value}`) })))
const scopes = computed(() => [
  { value: 'all', label: t('responses.export.scope.all', { n: number(total.value) }, total.value) },
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
  if (!formId.value) return
  const id = formId.value
  const created = await run(() =>
    api.post<ResponseExport>(`/forms/${id}/responses/export`, {
      format: format.value,
      scope: scope.value,
      query: scope.value === 'filtered' ? props.query : {},
      ids: scope.value === 'selected' ? props.selectedIds : [],
      columns: allQuestions.value || !props.columns.length ? [] : props.columns,
      details: details.value,
    }),
  )
  if (!created) return
  job.value = created.data
  emit('created')
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
  <AppModal v-model:open="open" :title="t('responses.export.title')" :description="t('responses.export.desc')" :dismissible="!busy && !job" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div v-if="!job" class="flex flex-col gap-5">
        <UFormField v-if="!props.formId" :label="t('responses.export.form')" required>
          <USelectMenu
            v-model="pickedId"
            :items="formItems"
            value-key="value"
            :loading="formsLoading"
            :placeholder="t('responses.export.pickForm')"
            :search-input="{ placeholder: t('responses.byForm.search') }"
            icon="i-lucide-file-text"
            class="w-full"
          />
        </UFormField>
        <UFormField :label="t('responses.export.formatLabel')">
          <URadioGroup v-model="format" :items="formats" variant="card" color="neutral" class="w-full" />
        </UFormField>
        <UFormField :label="t('responses.export.which')">
          <URadioGroup v-model="scope" :items="scopes" color="neutral" />
        </UFormField>
        <div class="flex flex-col gap-3 border-t border-default pt-4">
          <USwitch
            v-if="columns.length"
            v-model="allQuestions" color="neutral" :label="t('responses.export.allQuestions')" :description="allQuestions ? t('responses.export.allQuestionsOn') : t('responses.export.allQuestionsOff', { n: columns.length }, columns.length)" />
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
          <UButton :label="t('responses.export.start')" icon="i-lucide-file-down" color="neutral" :loading="busy" :disabled="!formId" @click="start" />
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

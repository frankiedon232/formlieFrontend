<!--
  One response, in a panel from the side (F11): number and respondent in the header with previous /
  next (K / J, also the arrow buttons) through the list; status and tags (saved at once); when,
  how long, how it came in, language, device, version; a possible duplicate links to the earlier
  response; every answer grouped by page; notes and history. Esc closes. Phones: full width.
-->
<script setup lang="ts">
import { RESPONSE_STATUSES, type ResponseDetail, type ResponseStatus } from '#shared/types/responses'
import { APP_LOCALES } from '#shared/utils/i18n/locales'
import { isInputField } from '#shared/utils/forms/fields'

const props = defineProps<{ id: string | null; ids: string[] }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ go: [id: string]; changed: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { dateTime, relative } = useFormat()
const { duration } = useResponseFormat()

const response = ref<ResponseDetail | null>(null)
const loading = ref(false)
const failed = ref(false)
async function load(id: string) {
  loading.value = true
  failed.value = false
  try {
    response.value = (await api.get<ResponseDetail>(`/responses/${id}`)).data
  } catch (error) {
    failed.value = true
    handle(error)
  } finally {
    loading.value = false
  }
}
watch(() => [props.id, open.value] as const, ([id, isOpen]) => id && isOpen && void load(id), { immediate: true })

const index = computed(() => (props.id ? props.ids.indexOf(props.id) : -1))
const prev = computed(() => (index.value > 0 ? props.ids[index.value - 1] : null))
const next = computed(() => (index.value >= 0 && index.value < props.ids.length - 1 ? props.ids[index.value + 1] : null))
defineShortcuts({
  j: { usingInput: false, handler: () => open.value && next.value && emit('go', next.value) },
  k: { usingInput: false, handler: () => open.value && prev.value && emit('go', prev.value) },
})

// Status and tags: saved at once, one change at a time.
const { busy, run } = useBusy()
async function save(body: { status?: ResponseStatus; tags?: string[] }) {
  if (!response.value) return
  const id = response.value.id
  await run(async () => {
    const { data } = await api.patch<ResponseDetail>(`/responses/${id}`, body)
    if (response.value?.id === id) response.value = data
    emit('changed')
  })
}
const statusItems = computed(() => RESPONSE_STATUSES.map(value => ({ value, label: t(`status.${value}`), icon: RESPONSE_STATUS_META[value].icon })))

const pages = computed(() =>
  (response.value?.schema.pages ?? [])
    .map(page => ({ ...page, fields: page.rows.flatMap(row => row.fields).filter(field => isInputField(field.type) && field.type !== 'payment') }))
    .filter(page => page.fields.length),
)
const facts = computed(() => {
  const r = response.value
  if (!r) return []
  return [
    { icon: 'i-lucide-calendar-clock', label: dateTime(r.submitted_at), hint: relative(r.submitted_at) },
    ...(r.duration_seconds != null ? [{ icon: 'i-lucide-timer', label: duration(r.duration_seconds), hint: t('responses.detail.timeTaken') }] : []),
    { icon: r.channel === 'embed' ? 'i-lucide-code-xml' : r.channel === 'api' ? 'i-lucide-plug' : 'i-lucide-link', label: t(`responses.channel.${r.channel}`), hint: t('responses.detail.cameIn') },
    { icon: APP_LOCALES.find(item => item.code === r.language)?.flag ?? 'i-lucide-languages', label: APP_LOCALES.find(item => item.code === r.language)?.name ?? r.language, hint: t('responses.detail.language') },
    { icon: r.meta.device === 'Phone' ? 'i-lucide-smartphone' : r.meta.device === 'Tablet' ? 'i-lucide-tablet' : 'i-lucide-monitor', label: t(`responses.device.${r.meta.device.toLowerCase()}`), hint: t('responses.detail.device') },
    ...(r.form_version ? [{ icon: 'i-lucide-history', label: `v${r.form_version}`, hint: t('responses.detail.version') }] : []),
  ]
})
const title = computed(() => (response.value ? response.value.respondent.name || response.value.respondent.email || t('responses.anonymous') : t('common.loading')))
</script>

<template>
  <USlideover v-model:open="open" :content="{ onOpenAutoFocus: (event: Event) => event.preventDefault() }" :title="title" :description="response ? `#${response.number} · ${response.form.name}` : undefined" :ui="{ content: 'w-full sm:max-w-2xl', body: 'flex flex-col gap-6' }">
    <template #actions>
      <UTooltip :text="t('responses.detail.previous')" :kbds="['k']">
        <UButton icon="i-lucide-chevron-up" color="neutral" variant="outline" size="sm" square :disabled="!prev" :aria-label="t('responses.detail.previous')" @click="prev && emit('go', prev)" />
      </UTooltip>
      <UTooltip :text="t('responses.detail.next')" :kbds="['j']">
        <UButton icon="i-lucide-chevron-down" color="neutral" variant="outline" size="sm" square :disabled="!next" :aria-label="t('responses.detail.next')" @click="next && emit('go', next)" />
      </UTooltip>
    </template>

    <template #body>
      <div v-if="loading && !response" class="flex flex-col gap-4" :aria-label="t('common.loading')">
        <USkeleton class="h-9 w-full" />
        <USkeleton v-for="n in 6" :key="n" class="h-12 w-full" />
      </div>
      <UEmpty v-else-if="failed && !response" icon="i-lucide-cloud-alert" :title="t('dataView.errorTitle')" :actions="[{ label: t('common.retry'), color: 'neutral', variant: 'outline', onClick: () => id && load(id) }]" variant="naked" />

      <template v-else-if="response">
        <div class="flex flex-col gap-5 transition-opacity" :class="loading ? 'opacity-60' : ''" :aria-busy="loading || undefined">
          <!-- Review: status and tags -->
          <div class="grid gap-3 sm:grid-cols-[12rem_minmax(0,1fr)]">
            <UFormField :label="t('responses.list.status')">
              <USelect
                :model-value="response.status"
                :items="statusItems"
                :loading="busy"
                :disabled="!response.can.review"
                class="w-full"
                @update:model-value="value => save({ status: value as ResponseStatus })"
              />
            </UFormField>
            <UFormField :label="t('responses.detail.tags')">
              <UInputTags
                :model-value="response.tags"
                :placeholder="t('responses.detail.addTag')"
                :disabled="!response.can.review || busy"
                :max-length="40"
                class="w-full"
                @update:model-value="tags => save({ tags: tags as string[] })"
              />
            </UFormField>
          </div>

          <!-- Facts -->
          <ul class="flex flex-wrap gap-2">
            <li v-for="fact in facts" :key="fact.hint" class="flex items-center gap-1.5 rounded-md border border-default px-2.5 py-1 text-xs">
              <UIcon :name="fact.icon" class="size-3.5 shrink-0 text-muted" />
              <span class="text-default">{{ fact.label }}</span>
              <span class="sr-only">{{ fact.hint }}</span>
            </li>
          </ul>

          <UAlert
            v-if="response.possible_duplicate"
            icon="i-lucide-copy"
            color="warning"
            variant="subtle"
            :title="t('responses.detail.duplicateTitle')"
            :description="t('responses.detail.duplicateDesc')"
            :actions="[{ label: t('responses.detail.openEarlier'), color: 'neutral', variant: 'outline', onClick: () => emit('go', response!.possible_duplicate!.of) }]"
          />
        </div>

        <!-- Answers by page -->
        <section v-for="page in pages" :key="page.id" class="flex flex-col gap-3">
          <h3 v-if="pages.length > 1 || page.title" class="text-xs font-medium text-muted uppercase">{{ page.title || t('preview.page', { n: pages.indexOf(page) + 1 }) }}</h3>
          <dl class="flex flex-col divide-y divide-default rounded-lg border border-default">
            <div v-for="field in page.fields" :key="field.id" class="grid gap-1 px-4 py-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] sm:gap-4">
              <dt class="text-sm text-muted">{{ field.label || field.key }}</dt>
              <dd class="min-w-0"><FormsResponsesAnswer :field="field" :value="response.data[field.key]" /></dd>
            </div>
          </dl>
        </section>

        <FormsResponsesNotes :response="response" @updated="value => ((response = value), emit('changed'))" />
      </template>
    </template>
  </USlideover>
</template>

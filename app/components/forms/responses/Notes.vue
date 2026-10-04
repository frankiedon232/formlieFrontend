<!--
  Notes and history of a response (F11): notes for the team (never shown to the respondent), newest
  first, with a box to add one (Ctrl / ⌘ + Enter sends); then every change (status, tags, answers)
  as a slim timeline.
-->
<script setup lang="ts">
import type { ResponseDetail } from '#shared/types/responses'

const props = defineProps<{ response: ResponseDetail }>()
const emit = defineEmits<{ updated: [response: ResponseDetail] }>()
const { t } = useI18n()
const api = useApi()
const { relative, dateTime } = useFormat()
const { busy, run } = useBusy()

const draft = ref('')
watch(() => props.response.id, () => (draft.value = ''))
async function add() {
  const text = draft.value.trim()
  if (!text) return
  await run(async () => {
    const { data } = await api.post<ResponseDetail>(`/responses/${props.response.id}/notes`, { text })
    draft.value = ''
    emit('updated', data)
  })
}

const fieldLabel = (field: string) => {
  if (field === 'status') return t('responses.list.status')
  if (field === 'tags') return t('responses.detail.tags')
  if (field === 'note') return t('responses.detail.note')
  const key = field.replace(/^answer:/, '')
  return props.response.schema.pages.flatMap(page => page.rows.flatMap(row => row.fields)).find(item => item.key === key)?.label ?? key
}
const show = (value: unknown, field: string) => {
  if (value == null || value === '') return '–'
  if (field === 'status') return t(`status.${value}`)
  if (Array.isArray(value)) return value.join(', ') || '–'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('responses.detail.notes') }}</h3>
    <form class="flex flex-col gap-2" @submit.prevent="add">
      <UTextarea
        v-model="draft"
        :rows="2"
        autoresize
        :maxrows="8"
        :placeholder="t('responses.detail.notePlaceholder')"
        :aria-label="t('responses.detail.addNote')"
        class="w-full"
        @keydown.meta.enter.prevent="add"
        @keydown.ctrl.enter.prevent="add"
      />
      <div class="flex items-center justify-between gap-2">
        <span class="text-[11px] text-dimmed">{{ t('responses.detail.noteHint') }}</span>
        <UButton type="submit" :label="t('responses.detail.addNote')" color="neutral" size="sm" :loading="busy" :disabled="!draft.trim()" />
      </div>
    </form>
    <ul v-if="response.notes.length" class="flex flex-col gap-2">
      <li v-for="note in response.notes" :key="note.id" class="rounded-md border border-default bg-elevated/40 p-3">
        <div class="mb-1 flex items-center gap-2 text-xs">
          <UAvatar :alt="note.author.name" size="3xs" />
          <span class="font-medium text-highlighted">{{ note.author.name }}</span>
          <UTooltip :text="dateTime(note.created_at)"><span class="text-muted">{{ relative(note.created_at) }}</span></UTooltip>
        </div>
        <p class="text-sm whitespace-pre-line text-default">{{ note.text }}</p>
      </li>
    </ul>
  </section>

  <section v-if="response.history.length" class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('responses.detail.history') }}</h3>
    <ol class="flex flex-col">
      <li v-for="change in response.history" :key="change.id" class="flex gap-3 border-s border-default ps-3 pb-3 last:pb-0">
        <div class="flex min-w-0 flex-col gap-0.5 text-sm">
          <span class="text-default">
            <span class="font-medium text-highlighted">{{ change.by.name }}</span>
            {{ t('responses.detail.changed', { field: fieldLabel(change.field) }) }}
          </span>
          <span v-if="change.field !== 'note'" class="truncate text-xs text-muted">{{ show(change.before, change.field) }} → {{ show(change.after, change.field) }}</span>
          <UTooltip :text="dateTime(change.at)"><span class="w-fit text-[11px] text-dimmed">{{ relative(change.at) }}</span></UTooltip>
        </div>
      </li>
    </ol>
  </section>
</template>

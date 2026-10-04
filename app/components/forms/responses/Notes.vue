<!--
  Notes on a response (F11): for the team only (never shown to the respondent), newest first, with
  a box to add one (Ctrl / ⌘ + Enter sends). The change history stays in the audit trail; the panel
  shows only what matters (owner, 2026-10-04).
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
</template>

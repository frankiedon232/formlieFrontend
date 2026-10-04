<!--
  A response as a grid card (F11, DataView Grid): respondent and status on top, three answers,
  then number, when, and notes. The whole card opens the response.
-->
<script setup lang="ts">
import type { ResponseRow } from '#shared/types/responses'
import type { FormField } from '#shared/utils/forms/build'

defineProps<{ row: ResponseRow; fields: FormField[] }>()
const emit = defineEmits<{ open: [] }>()
const { t } = useI18n()
const { relative } = useFormat()
const { text } = useResponseFormat()
</script>

<template>
  <UCard
    variant="outline"
    class="h-full cursor-pointer transition-colors hover:border-accented"
    :ui="{ body: 'flex h-full flex-col gap-3 p-4 sm:p-4' }"
    @click="emit('open')"
  >
    <div class="flex items-start justify-between gap-2">
      <FormsResponsesWho :row="row" @open="emit('open')" />
      <DataStatusBadge :status="row.status" />
    </div>
    <p v-if="!fields.length" class="flex min-w-0 items-center gap-1.5 text-sm text-default">
      <UIcon name="i-lucide-file-text" class="size-3.5 shrink-0 text-muted" /><span class="truncate">{{ row.form.name }}</span>
    </p>
    <dl v-if="fields.length" class="flex flex-col gap-2">
      <div v-for="field in fields" :key="field.key" class="flex min-w-0 flex-col">
        <dt class="truncate text-[11px] text-muted">{{ field.label }}</dt>
        <dd class="truncate text-sm text-default">{{ text(field, row.answers[field.key]) || '–' }}</dd>
      </div>
    </dl>
    <div class="mt-auto flex items-center gap-2 border-t border-default pt-3 text-xs text-muted">
      <span class="tabular-nums">#{{ row.number }}</span>
      <span class="text-dimmed">·</span>
      <span>{{ relative(row.submitted_at) }}</span>
      <span v-if="row.notes_count" class="ms-auto inline-flex items-center gap-1"><UIcon name="i-lucide-message-square" class="size-3.5" />{{ row.notes_count }}</span>
      <span v-if="row.tags.length" class="ms-auto truncate" :class="row.notes_count ? 'ms-2' : ''">{{ row.tags.map(tag => `#${tag}`).join(' ') }}</span>
    </div>
    <span class="sr-only">{{ t('responses.list.open') }}</span>
  </UCard>
</template>

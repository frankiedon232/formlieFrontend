<!--
  A response as a grid card, in the design's task-card style (docs/design 084447; owner 2026-10-04):
  a "when" pill, status and ⋯ (open, mark as…, delete) on top; the respondent as the title (a red
  flag for a possible duplicate) with email or form below; up to four answers in a two-column grid;
  a divider, then how complete it is ("Answered 7 / 9" with a black bar, like the design's
  Progress); avatar, number and counts (files, notes, time) at the bottom. Same structure in every
  card, so cards line up row by row.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ResponseRow } from '#shared/types/responses'
import type { FormField } from '#shared/utils/forms/build'

const props = defineProps<{ row: ResponseRow; fields: FormField[]; actions: DropdownMenuItem[][] }>()
const emit = defineEmits<{ open: [] }>()
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const { text, duration } = useResponseFormat()

const name = computed(() => props.row.respondent.title || `#${props.row.number}`)
const sub = computed(() => (props.row.respondent.name && props.row.respondent.email ? props.row.respondent.email : t(`responses.respondentKind.${props.row.respondent.kind === 'anonymous' ? 'answer' : props.row.respondent.kind}`)))
const share = computed(() => (props.row.questions ? props.row.answered / props.row.questions : 0))
const max = (field: FormField) => Number(field.props?.max ?? (field.type === 'rating' ? 5 : field.type === 'scale' ? 10 : 100))
const value = (field: FormField) => props.row.answers[field.key]
const answered = (field: FormField) => {
  const v = value(field)
  return v != null && v !== '' && !(Array.isArray(v) && !v.length)
}
/** The inbox has no answers: the form and how it came in fill the same two-column grid. */
const facts = computed(() =>
  props.fields.length
    ? []
    : [
        { label: t('responses.list.form'), value: props.row.form.name },
        { label: t('responses.detail.cameIn'), value: t(`responses.channel.${props.row.channel}`) },
      ],
)
</script>

<template>
  <article class="group flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md">
    <!-- When · status · menu -->
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon name="i-lucide-calendar-clock" class="size-3.5 shrink-0 text-muted" />
        <span class="truncate">{{ relative(row.submitted_at) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5" @click.stop>
        <DataStatusBadge :status="row.status" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <!-- Who -->
    <div class="mt-3 flex min-w-0 items-center gap-1.5">
      <UTooltip v-if="row.possible_duplicate" :text="t('responses.list.possibleDuplicate')">
        <UIcon name="i-lucide-flag" class="size-4 shrink-0 text-error" :aria-label="t('responses.list.possibleDuplicate')" />
      </UTooltip>
      <button type="button" class="truncate text-start text-base font-semibold text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" @click.stop="emit('open')">{{ name }}</button>
    </div>
    <p class="truncate text-sm text-muted" :dir="row.respondent.name && row.respondent.email ? 'ltr' : undefined">{{ sub }}</p>

    <!-- Answers (two columns, one line each) -->
    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-2.5">
      <div v-for="field in fields" :key="field.key" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ field.label || field.key }}</dt>
        <dd class="flex h-5 min-w-0 items-center">
          <span v-if="!answered(field)" class="text-sm text-dimmed">–</span>
          <span v-else-if="field.type === 'rating'" class="flex items-center gap-0.5" :aria-label="text(field, value(field))">
            <svg v-for="n in max(field)" :key="n" viewBox="0 0 24 24" class="size-3.5" :class="n <= Number(value(field)) ? 'text-highlighted' : 'text-dimmed'" aria-hidden="true">
              <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" :fill="n <= Number(value(field)) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" />
            </svg>
          </span>
          <span v-else-if="field.type === 'scale' || field.type === 'slider'" class="flex w-full items-center gap-2">
            <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-elevated"><span class="block h-full rounded-full bg-inverted" :style="{ width: `${(Number(value(field)) / max(field)) * 100}%` }" /></span>
            <span class="text-xs font-medium text-highlighted tabular-nums">{{ number(Number(value(field))) }}</span>
          </span>
          <span v-else class="truncate text-sm text-default">{{ text(field, value(field)) }}</span>
        </dd>
      </div>
      <div v-for="fact in facts" :key="fact.label" class="flex min-w-0 flex-col gap-0.5">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="h-5 truncate text-sm text-default">{{ fact.value }}</dd>
      </div>
    </dl>

    <!-- How complete (the design's Progress) -->
    <div class="mt-auto pt-4">
      <div class="border-t border-default pt-3">
        <div class="mb-1.5 flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('responses.card.answered') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ row.answered }} / {{ row.questions }} · {{ percent(share) }}</span>
        </div>
        <div class="h-1.5 overflow-hidden rounded-full bg-elevated" role="presentation">
          <div class="h-full rounded-full bg-inverted" :style="{ width: `${share * 100}%` }" />
        </div>
      </div>

      <!-- Avatar, number, counts -->
      <div class="mt-4 flex items-center justify-between gap-2">
        <div class="flex min-w-0 items-center gap-2">
          <UAvatar :alt="name" :icon="row.respondent.kind === 'anonymous' ? 'i-lucide-user-round' : undefined" size="xs" />
          <span class="text-xs text-muted tabular-nums">#{{ row.number }}</span>
        </div>
        <div class="flex items-center gap-3 text-xs text-muted">
          <span v-if="row.duration_seconds != null" class="flex items-center gap-1"><UIcon name="i-lucide-timer" class="size-3.5" />{{ duration(row.duration_seconds) }}</span>
          <span class="flex items-center gap-1" :class="row.files_count ? 'text-toned' : ''"><UIcon name="i-lucide-paperclip" class="size-3.5" />{{ row.files_count }}</span>
          <span class="flex items-center gap-1" :class="row.notes_count ? 'text-toned' : ''"><UIcon name="i-lucide-message-square" class="size-3.5" />{{ row.notes_count }}</span>
        </div>
      </div>
    </div>
  </article>
</template>

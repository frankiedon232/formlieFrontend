<!--
  A response as a rich grid card (F11, owner 2026-10-04: "make the card very rich"): a status
  colour edge, avatar, name and email with status; a facts row (number, when, time taken, how it
  came in, language); up to four answers shown by kind (stars, slim bars, choice chips, text) or
  the form (inbox); tags, notes and a possible-duplicate flag; quick Reviewed · Approve · Reject in
  the footer. The card opens the response; the quick buttons only change its status.
-->
<script setup lang="ts">
import type { ResponseRow, ResponseStatus } from '#shared/types/responses'
import type { FormField } from '#shared/utils/forms/build'
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ row: ResponseRow; fields: FormField[]; busy?: boolean }>()
const emit = defineEmits<{ open: []; status: [status: ResponseStatus] }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const { text, duration } = useResponseFormat()

const name = computed(() => props.row.respondent.name || props.row.respondent.email || t('responses.anonymous'))
const locale = computed(() => APP_LOCALES.find(item => item.code === props.row.language))
const max = (field: FormField) => Number(field.props?.max ?? (field.type === 'rating' ? 5 : field.type === 'scale' ? 10 : 100))
const answered = (field: FormField) => {
  const value = props.row.answers[field.key]
  return value != null && value !== '' && !(Array.isArray(value) && !value.length)
}
const options = (field: FormField) => new Map((field.options ?? []).map(option => [option.value, option.label]))
const quick = computed(() =>
  (['reviewed', 'approved', 'rejected'] as const).filter(status => status !== props.row.status),
)
</script>

<template>
  <article
    class="group relative flex h-full cursor-pointer flex-col overflow-hidden rounded-lg border border-default border-s-[3px] bg-default transition-all hover:-translate-y-0.5 hover:shadow-md focus-within:shadow-md"
    :class="RESPONSE_STATUS_META[row.status].edge"
    @click="emit('open')"
  >
    <!-- Who + status -->
    <header class="flex items-start gap-3 p-4 pb-3">
      <UAvatar :alt="row.respondent.name || row.respondent.email || '?'" :icon="row.respondent.kind === 'anonymous' ? 'i-lucide-user-round' : undefined" size="lg" />
      <div class="flex min-w-0 flex-1 flex-col">
        <button type="button" class="truncate text-start font-semibold text-highlighted focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)" @click.stop="emit('open')">{{ name }}</button>
        <span v-if="row.respondent.name && row.respondent.email" class="truncate text-xs text-muted" dir="ltr">{{ row.respondent.email }}</span>
        <span v-else class="text-xs text-muted">{{ t(`responses.respondentKind.${row.respondent.kind}`) }}</span>
      </div>
      <DataStatusBadge :status="row.status" />
    </header>

    <!-- Facts -->
    <ul class="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 pb-3 text-xs text-muted">
      <li class="font-medium text-toned tabular-nums">#{{ row.number }}</li>
      <li class="flex items-center gap-1"><UIcon name="i-lucide-clock-3" class="size-3.5" />{{ relative(row.submitted_at) }}</li>
      <li v-if="row.duration_seconds != null" class="flex items-center gap-1"><UIcon name="i-lucide-timer" class="size-3.5" />{{ duration(row.duration_seconds) }}</li>
      <li class="flex items-center gap-1">
        <UIcon :name="row.channel === 'embed' ? 'i-lucide-code-xml' : row.channel === 'api' ? 'i-lucide-plug' : 'i-lucide-link'" class="size-3.5" />{{ t(`responses.channel.${row.channel}`) }}
      </li>
      <li v-if="locale" class="flex items-center gap-1"><UIcon :name="locale.flag" class="size-3.5" />{{ locale.code.toUpperCase() }}</li>
    </ul>

    <!-- Answers (per form) or the form (inbox) -->
    <div class="mx-4 mb-3 flex flex-1 flex-col gap-2.5 rounded-md bg-elevated/40 p-3">
      <template v-if="fields.length">
        <div v-for="field in fields" :key="field.key" class="flex min-w-0 flex-col gap-1">
          <span class="truncate text-[11px] font-medium tracking-wide text-muted uppercase">{{ field.label || field.key }}</span>
          <span v-if="!answered(field)" class="text-sm text-dimmed">–</span>
          <span v-else-if="field.type === 'rating'" class="flex items-center gap-0.5" :aria-label="text(field, row.answers[field.key])">
            <svg v-for="n in max(field)" :key="n" viewBox="0 0 24 24" class="size-3.5" :class="n <= Number(row.answers[field.key]) ? 'text-highlighted' : 'text-dimmed'" aria-hidden="true">
              <path d="M12 2.5l2.9 6.1 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.3 1.3-6.6-4.9-4.6 6.6-.8z" :fill="n <= Number(row.answers[field.key]) ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.8" />
            </svg>
          </span>
          <span v-else-if="field.type === 'scale' || field.type === 'slider'" class="flex items-center gap-2">
            <span class="h-1.5 flex-1 overflow-hidden rounded-full bg-accented/60"><span class="block h-full rounded-full bg-inverted" :style="{ width: `${(Number(row.answers[field.key]) / max(field)) * 100}%` }" /></span>
            <span class="text-xs font-medium text-highlighted tabular-nums">{{ number(Number(row.answers[field.key])) }}</span>
          </span>
          <span v-else-if="field.type === 'checkbox' || field.type === 'multi_select'" class="flex flex-wrap gap-1">
            <UBadge v-for="pick in (row.answers[field.key] as string[]).slice(0, 3)" :key="pick" :label="options(field).get(pick) ?? pick" color="neutral" variant="outline" size="sm" class="max-w-full rounded-md" />
            <UBadge v-if="(row.answers[field.key] as string[]).length > 3" :label="`+${(row.answers[field.key] as string[]).length - 3}`" color="neutral" variant="soft" size="sm" class="rounded-md" />
          </span>
          <span v-else class="line-clamp-2 text-sm text-default">{{ text(field, row.answers[field.key]) }}</span>
        </div>
      </template>
      <div v-else class="flex min-w-0 items-center gap-2.5">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-default text-muted ring-1 ring-(--ui-border)"><UIcon name="i-lucide-file-text" class="size-4" /></span>
        <div class="flex min-w-0 flex-col">
          <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('responses.list.form') }}</span>
          <span class="truncate text-sm font-medium text-highlighted">{{ row.form.name }}</span>
        </div>
      </div>
    </div>

    <!-- Tags and flags -->
    <div v-if="row.tags.length || row.notes_count || row.possible_duplicate || row.edited" class="flex flex-wrap items-center gap-1.5 px-4 pb-3">
      <UBadge v-if="row.possible_duplicate" :label="t('responses.list.possibleDuplicate')" icon="i-lucide-copy" color="warning" variant="subtle" size="sm" class="rounded-md" />
      <UBadge v-for="tag in row.tags" :key="tag" :label="`#${tag}`" color="neutral" variant="soft" size="sm" class="rounded-md" />
      <UBadge v-if="row.notes_count" :label="String(row.notes_count)" icon="i-lucide-message-square" color="neutral" variant="outline" size="sm" class="rounded-md" />
      <UBadge v-if="row.edited" :label="t('responses.card.edited')" icon="i-lucide-pencil" color="neutral" variant="outline" size="sm" class="rounded-md" />
    </div>

    <!-- Quick review -->
    <footer class="mt-auto flex items-center gap-1 border-t border-default bg-elevated/30 px-2 py-1.5" @click.stop>
      <UButton
        v-for="status in quick"
        :key="status"
        :label="t(`responses.card.quick.${status}`)"
        :icon="RESPONSE_STATUS_META[status].icon"
        color="neutral"
        variant="ghost"
        size="xs"
        :disabled="busy"
        :ui="{ label: 'hidden 2xl:inline', leadingIcon: RESPONSE_STATUS_META[status].text }"
        :aria-label="t(`responses.card.quick.${status}`)"
        @click="emit('status', status)"
      />
      <UButton :label="t('responses.list.open')" trailing-icon="i-lucide-arrow-right" color="neutral" variant="ghost" size="xs" class="ms-auto rtl:[&_svg]:rotate-180" @click="emit('open')" />
    </footer>
  </article>
</template>

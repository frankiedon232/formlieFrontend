<!--
  Every answer of a response, grouped by likeness (F11; owner 2026-10-04: use the space, group like
  with like, no endless scrolling on long forms). Filter chips on top (All · People & contact ·
  Choices · Ratings · Written · Numbers & dates · Files · Other, with counts) in a rounded track
  without a scrollbar (AppChipScroller: wheel, arrows, a clicked chip centres) and "Only answered". Each group: a header with how many were answered, then tiles in
  two columns that share one height per row; long text and grids take the full width. Files flow
  (owner 2026-10-04): each question's tile is as wide as its files, side by side, wrapping when full.
  Editors see a pencil on every answer that can be changed (F11 M2; opens EditAnswer); a changed
  answer carries an "Edited" mark with who changed it, when, and what it was before.
-->
<script setup lang="ts">
import type { ResponseChange, ResponseDetail } from '#shared/types/responses'
import type { FormField } from '#shared/utils/forms/build'
import { canEditAnswer } from '#shared/utils/forms/answer-edit'
import { FIELD_TYPES, isInputField } from '#shared/utils/forms/fields'

const props = defineProps<{ response: ResponseDetail }>()
const emit = defineEmits<{ updated: [response: ResponseDetail] }>()
const { t } = useI18n()
const { relative, dateTime } = useFormat()
const { text } = useResponseFormat()

const filled = (value: unknown) => value != null && value !== '' && !(Array.isArray(value) && !value.length)
const fields = computed(() =>
  props.response.schema.pages.flatMap(page => page.rows.flatMap(row => row.fields)).filter(field => isInputField(field.type) && field.type !== 'payment' && field.type !== 'hidden'),
)
const onlyAnswered = ref(false)
const group = ref<AnswerGroup | 'all'>('all')
watch(() => props.response.form.id, () => (group.value = 'all'))

const groups = computed(() =>
  ANSWER_GROUPS.map(item => {
    const inGroup = fields.value.filter(field => answerGroup(field) === item.key)
    return { ...item, fields: inGroup, answered: inGroup.filter(field => filled(props.response.data[field.key])).length }
  }).filter(item => item.fields.length),
)
const shown = computed(() =>
  groups.value
    .filter(item => group.value === 'all' || item.key === group.value)
    .map(item => ({ ...item, fields: onlyAnswered.value ? item.fields.filter(field => filled(props.response.data[field.key])) : item.fields }))
    .filter(item => item.fields.length),
)
const icon = (type: string) => (FIELD_TYPES as Record<string, { icon: string }>)[type]?.icon ?? 'i-lucide-circle-help'
const total = computed(() => fields.value.length)
const answeredTotal = computed(() => fields.value.filter(field => filled(props.response.data[field.key])).length)

// Editing (people with "Can edit"): the latest change per answer, and the dialog.
const editable = (field: FormField) => props.response.can.edit && canEditAnswer(field)
const lastEdit = computed(() => {
  const map = new Map<string, ResponseChange>()
  for (const change of props.response.history) if (change.field.startsWith('answer:') && !map.has(change.field.slice(7))) map.set(change.field.slice(7), change)
  return map
})
const editHint = (field: FormField, change: ResponseChange) =>
  t('responses.edit.mark', { who: change.by.name, when: relative(change.at), before: filled(change.before) ? text(field, change.before) : t('responses.detail.noAnswer') })
const editing = ref<FormField | null>(null)
const editOpen = ref(false)
function edit(field: FormField) {
  editing.value = field
  editOpen.value = true
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-3">
      <h3 class="text-xs font-medium text-muted uppercase">{{ t('responses.detail.answers') }}</h3>
      <USwitch v-model="onlyAnswered" size="sm" :label="t('responses.detail.onlyAnswered')" :ui="{ label: 'text-xs text-muted' }" />
    </div>

    <!-- Group chips: a rounded track (wheel, arrows, click centres the chip) -->
    <AppChipScroller :label="t('responses.detail.groups')">
      <button
        v-for="item in [{ key: 'all' as const, icon: 'i-lucide-layout-grid', answered: answeredTotal, fields: { length: total } }, ...groups]"
        :key="item.key"
        type="button"
        data-chip
        :aria-pressed="group === item.key"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
        :class="group === item.key ? 'bg-default text-highlighted shadow-xs ring-1 ring-(--ui-border)' : 'text-muted hover:text-highlighted'"
        @click="group = item.key"
      >
        <UIcon :name="item.icon" class="size-3.5" />
        {{ t(`responses.groups.${item.key}`) }}
        <span class="tabular-nums opacity-70">{{ item.answered }}/{{ item.fields.length }}</span>
      </button>
    </AppChipScroller>

    <div v-for="item in shown" :key="item.key" class="flex flex-col gap-2">
      <div v-if="group === 'all'" class="flex items-center gap-2 pt-1 text-xs text-muted">
        <UIcon :name="item.icon" class="size-3.5" />
        <span class="font-medium text-toned">{{ t(`responses.groups.${item.key}`) }}</span>
        <span class="h-px flex-1 bg-(--ui-border)" />
        <span class="tabular-nums">{{ t('responses.detail.answeredOf', { n: item.answered, total: item.fields.length }) }}</span>
      </div>
      <dl :class="item.key === 'files' ? 'flex flex-wrap gap-2' : 'grid gap-2 sm:grid-cols-2'">
        <div
          v-for="field in item.fields"
          :key="field.id"
          class="group/tile flex h-full min-w-0 flex-col gap-2 rounded-lg border border-default p-3"
          :class="[item.key === 'files' ? 'max-w-full min-w-40 flex-auto sm:flex-none' : wideAnswer(field) ? 'sm:col-span-2' : '', filled(response.data[field.key]) ? 'bg-default' : 'bg-elevated/30']"
        >
          <dt class="flex items-start gap-2 text-xs text-muted">
            <UIcon :name="icon(field.type)" class="mt-px size-3.5 shrink-0" />
            <!-- w-0 + flex-1: a long question wraps instead of widening a file tile -->
            <span class="line-clamp-2 w-0 min-w-0 flex-1">{{ field.label || field.key }}</span>
            <UTooltip v-if="lastEdit.get(field.key)" :text="editHint(field, lastEdit.get(field.key)!)">
              <UBadge :label="t('responses.edit.edited')" icon="i-lucide-pencil-line" color="warning" variant="subtle" size="sm" class="-my-0.5 shrink-0 rounded-md" :title="dateTime(lastEdit.get(field.key)!.at)" />
            </UTooltip>
            <UButton
              v-if="editable(field)"
              icon="i-lucide-pencil"
              color="neutral"
              variant="ghost"
              size="xs"
              square
              class="-my-1 -me-1 shrink-0 opacity-100 transition-opacity focus-visible:opacity-100 sm:opacity-0 sm:group-hover/tile:opacity-100"
              :aria-label="t('responses.edit.open', { field: field.label || field.key })"
              @click="edit(field)"
            />
          </dt>
          <dd class="min-w-0"><FormsResponsesAnswer :field="field" :value="response.data[field.key]" :response-id="response.id" /></dd>
        </div>
      </dl>
    </div>
    <AppEmpty v-if="!shown.length" icon="i-lucide-filter-x" :title="t('responses.detail.nothingHere')" variant="naked" size="sm" />
    <FormsResponsesEditAnswer v-if="response.can.edit" v-model:open="editOpen" :response="response" :field="editing" @saved="value => emit('updated', value)" />
  </section>
</template>

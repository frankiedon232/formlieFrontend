<!--
  The assistant in the builder (F19 M3): Suggest fields · Write help texts · Add logic · Check my form, on
  the form as it is being edited (unsaved changes included). Each suggestion is applied (one undo step, saved
  with the draft as usual) or skipped; "Apply all" takes the rest. On close, the history learns how many were
  taken (none = put aside). Opened from the builder header (A) on build and logic.
-->
<script setup lang="ts">
import type { AiAssistAction, AiAssistResult, AiSuggestion } from '#shared/types/ai'
import { AI_ASSIST_ACTIONS } from '#shared/types/ai'
import { AI_KIND_META } from '#shared/utils/ai/kinds'
import { allFields, keyFromLabel, newId } from '#shared/utils/forms/build'
import { FIELD_TYPES, type FieldType } from '#shared/utils/forms/fields'

const props = defineProps<{ formId: string }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const ai = useAi()
const builder = useBuilder()

const ACTIONS: Record<AiAssistAction, string> = { fields: 'i-lucide-list-plus', help: 'i-lucide-message-square-text', logic: 'i-lucide-git-branch', check: 'i-lucide-scan-search' }
const action = ref<AiAssistAction | null>(null)
const result = ref<AiAssistResult | null>(null)
const asking = ref(false)
const done = ref<Record<string, 'applied' | 'skipped'>>({})
const applied = computed(() => Object.values(done.value).filter(state => state === 'applied').length)
const waiting = computed(() => (result.value?.suggestions ?? []).filter(item => !done.value[item.id] && applicable(item)))

async function ask(next: AiAssistAction) {
  if (asking.value || !builder.schema.value) return
  await settle()
  action.value = next
  asking.value = true
  result.value = null
  done.value = {}
  try {
    result.value = (await api.post<AiAssistResult>(`/ai/forms/${props.formId}/assist`, { action: next, schema: builder.schema.value })).data
  } catch (error) {
    handle(error)
    action.value = null
  } finally {
    asking.value = false
  }
}

/** Tell the history how many were taken (none = put aside), once per request. */
async function settle() {
  const current = result.value
  if (!current?.suggestions.length) return
  result.value = null
  try {
    if (applied.value) await api.post(`/ai/requests/${current.request_id}/apply`, { count: applied.value }, { background: true })
    else await api.post(`/ai/requests/${current.request_id}/discard`, undefined, { background: true })
  } catch {
    // The changes are in the form either way; the history entry simply stays "waiting for review"
  }
}
watch(open, value => !value && void settle())
onBeforeUnmount(() => void settle())

/** A suggestion can still be applied (its field is still there, nothing to change otherwise). */
function applicable(item: AiSuggestion) {
  if (item.kind === 'set_help') return !!builder.findField(item.field_id)
  if (item.kind === 'add_rule') return true
  if (item.kind === 'fix') return (!!item.patch || !!item.remove) && (!item.field_id || !!builder.findField(item.field_id))
  return true
}

function apply(item: AiSuggestion) {
  const schema = builder.schema.value
  if (!schema || done.value[item.id]) return
  if (item.kind === 'add_field') {
    const keys = [...allFields(schema).map(field => field.key), ...builder.publishedKeys.value]
    const field = { ...structuredClone(toRaw(item.field)), id: newId('fld'), key: keyFromLabel(item.field.label, keys) }
    const page = schema.pages.find(entry => entry.id === item.page_id) ?? schema.pages.at(-1)!
    builder.place(field, { pageId: page.id, rowIndex: page.rows.length })
  } else if (item.kind === 'set_help') builder.updateField(item.field_id, { help: item.help })
  else if (item.kind === 'add_rule') {
    builder.history.record()
    schema.logic = [...(schema.logic ?? []), { ...structuredClone(toRaw(item.rule)), id: newId('rule') }]
  } else if (item.kind === 'fix') {
    if (item.remove && item.field_id) builder.remove([item.field_id])
    else if (item.patch && item.field_id) builder.updateField(item.field_id, item.patch)
  }
  done.value = { ...done.value, [item.id]: 'applied' }
}
const skip = (item: AiSuggestion) => (done.value = { ...done.value, [item.id]: 'skipped' })
function applyAll() {
  const list = waiting.value
  for (const item of list) apply(item)
  toast.add({ title: t('ai.assist.appliedAll', { n: list.length }, list.length), description: t('ai.assist.undoHint'), color: 'success', icon: 'i-lucide-circle-check' })
}

const titleOf = (item: AiSuggestion) =>
  item.kind === 'add_field' ? t('ai.assist.addField', { label: item.field.label }) : item.kind === 'set_help' ? item.label : item.kind === 'add_rule' ? t('ai.assist.addRule') : t(`ai.problem.${item.problem}`, { label: item.label || t('ai.assist.thisPage') })
const iconOf = (item: AiSuggestion) => (item.kind === 'add_field' ? (FIELD_TYPES[item.field.type as FieldType]?.icon ?? 'i-lucide-plus') : item.kind === 'set_help' ? 'i-lucide-message-square-text' : item.kind === 'add_rule' ? 'i-lucide-git-branch' : item.patch || item.remove ? 'i-lucide-wrench' : 'i-lucide-triangle-alert')
const applyLabel = (item: AiSuggestion) => (item.kind === 'fix' ? (item.remove ? t('ai.assist.remove') : t('ai.assist.fix')) : t('ai.assist.apply'))
</script>

<template>
  <USlideover v-model:open="open" :title="t('ai.assist.title')" :description="t('ai.assist.desc')" :ui="{ content: 'w-full sm:max-w-md', body: 'flex flex-col gap-4' }">
    <template #body>
      <AiOff v-if="!ai.enabled.value" size="sm" />
      <template v-else>
        <div class="grid grid-cols-2 gap-2">
          <button
            v-for="key in AI_ASSIST_ACTIONS"
            :key="key"
            type="button"
            class="flex flex-col gap-1 rounded-lg border p-3 text-start transition-all hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted) disabled:pointer-events-none disabled:opacity-60"
            :class="action === key ? 'border-inverted' : 'border-default'"
            :disabled="asking"
            :aria-pressed="action === key"
            @click="ask(key)"
          >
            <UIcon :name="asking && action === key ? 'i-lucide-loader-circle' : ACTIONS[key]" class="size-4 text-highlighted" :class="asking && action === key ? 'animate-spin' : ''" />
            <span class="text-sm font-medium text-highlighted">{{ t(`ai.assist.action.${key}`) }}</span>
            <span class="text-xs text-muted">{{ t(`ai.assist.actionHint.${key}`) }}</span>
          </button>
        </div>
        <p class="flex items-center gap-1.5 text-xs text-muted"><UIcon name="i-lucide-coins" class="size-3.5" />{{ t('ai.create.cost', { n: AI_KIND_META.builder.credits }, AI_KIND_META.builder.credits) }}</p>

        <div v-if="asking" class="flex flex-col gap-2" role="status" :aria-label="t('ai.create.thinking')">
          <USkeleton v-for="n in 4" :key="n" class="h-16 w-full rounded-lg" />
        </div>
        <template v-else-if="result">
          <AppEmpty v-if="!result.suggestions.length" size="sm" icon="i-lucide-circle-check" :title="t(`ai.assist.none.${result.action}`)" />
          <template v-else>
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm font-semibold text-highlighted">{{ t('ai.assist.found', { n: result.suggestions.length }, result.suggestions.length) }}</span>
              <UButton v-if="waiting.length > 1" :label="t('ai.assist.applyAll', { n: waiting.length })" icon="i-lucide-check-check" color="neutral" size="xs" @click="applyAll" />
            </div>
            <ul class="flex flex-col gap-2">
              <li v-for="item in result.suggestions" :key="item.id" class="flex flex-col gap-2 rounded-lg border border-default p-3 transition-opacity" :class="done[item.id] ? 'opacity-60' : ''">
                <div class="flex items-start gap-2.5">
                  <span class="flex size-7 shrink-0 items-center justify-center rounded-md border border-default"><UIcon :name="iconOf(item)" class="size-3.5 text-muted" /></span>
                  <div class="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span class="text-sm font-medium text-highlighted">{{ titleOf(item) }}</span>
                    <span v-if="item.kind === 'set_help'" class="text-xs text-muted italic">{{ item.help }}</span>
                    <span v-else-if="item.kind === 'add_field' || item.kind === 'add_rule'" class="text-xs text-muted">{{ t(`ai.note.${item.note.code}`, item.note.params ?? {}) }}</span>
                    <span v-else-if="item.kind === 'fix'" class="text-xs text-muted">{{ t(`ai.problemFix.${item.problem}`) }}</span>
                  </div>
                </div>
                <div class="flex items-center justify-end gap-1.5">
                  <UBadge v-if="done[item.id]" :label="t(`ai.assist.${done[item.id]}`)" :icon="done[item.id] === 'applied' ? 'i-lucide-check' : 'i-lucide-minus'" color="neutral" variant="soft" size="sm" class="rounded-md" />
                  <template v-else>
                    <UButton :label="t('ai.assist.skip')" color="neutral" variant="ghost" size="xs" @click="skip(item)" />
                    <UButton v-if="applicable(item)" :label="applyLabel(item)" color="neutral" variant="outline" size="xs" @click="apply(item)" />
                  </template>
                </div>
              </li>
            </ul>
          </template>
        </template>
        <AppEmpty v-else size="sm" icon="i-lucide-sparkles" :title="t('ai.assist.emptyTitle')" :description="t('ai.assist.emptyDesc')" />
      </template>
    </template>
    <template #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <span class="text-xs text-muted">{{ applied ? t('ai.assist.appliedCount', { n: applied }, applied) : t('ai.assist.undoHint') }}</span>
        <UButton :label="t('ai.assist.done')" color="neutral" @click="open = false" />
      </div>
    </template>
  </USlideover>
</template>

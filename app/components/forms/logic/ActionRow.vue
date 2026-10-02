<!-- One "then" line of a rule: action (show / hide / require / jump) · target field or page. -->
<script setup lang="ts">
import type { LogicAction } from '#shared/utils/forms/logic'

const props = defineProps<{ action: { action: LogicAction; target: string }; index: number; removable: boolean }>()
const emit = defineEmits<{ update: [patch: { action?: LogicAction; target?: string }]; remove: [] }>()
const { t } = useI18n()
const logic = useLogicRules()

const ACTIONS: { value: LogicAction; icon: string }[] = [
  { value: 'show', icon: 'i-lucide-eye' },
  { value: 'hide', icon: 'i-lucide-eye-off' },
  { value: 'require', icon: 'i-lucide-asterisk' },
  { value: 'jump', icon: 'i-lucide-corner-down-right' },
]
const actionItems = computed(() => ACTIONS.map(a => ({ ...a, label: t(`logic.action.${a.value}`) })))
const jump = computed(() => props.action.action === 'jump')
const targetItems = computed(() =>
  jump.value
    ? logic.pages.value.map(p => ({ value: p.id, label: logic.pageLabel(p.id), icon: 'i-lucide-file' }))
    : logic.fields.value
        .filter(f => props.action.action !== 'require' || f.type !== 'calculated')
        .map(f => ({ value: f.id, label: logic.label(f), icon: fieldIcon(f.type) })),
)

function pickAction(next: LogicAction) {
  // Switching between "field" and "page" targets clears the target.
  const switching = (next === 'jump') !== jump.value
  emit('update', { action: next, ...(switching ? { target: '' } : {}) })
}
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,2.2fr)_auto] sm:items-center">
    <USelect
      :model-value="action.action"
      :items="actionItems"
      :icon="ACTIONS.find(a => a.value === action.action)?.icon"
      :aria-label="t('logic.actionType', { n: index + 1 })"
      class="col-start-1 w-full sm:col-start-auto"
      @update:model-value="v => pickAction(v as LogicAction)"
    />
    <USelectMenu
      :model-value="action.target || undefined"
      :items="targetItems"
      value-key="value"
      :placeholder="jump ? t('logic.pickPage') : t('logic.pickField')"
      :search-input="{ placeholder: t('common.search') }"
      :aria-label="t('logic.actionTarget', { n: index + 1 })"
      class="col-start-1 w-full sm:col-start-auto"
      @update:model-value="v => v && emit('update', { target: String(v) })"
    />
    <UButton
      icon="i-lucide-x"
      color="neutral"
      variant="ghost"
      square
      :disabled="!removable"
      :aria-label="t('logic.removeAction', { n: index + 1 })"
      class="col-start-2 row-start-1 justify-self-end sm:col-start-auto sm:row-start-auto"
      @click="emit('remove')"
    />
  </div>
</template>

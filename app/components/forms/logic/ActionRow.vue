<!--
  One "then" line of a rule: what to do (each action explains itself in the list) · on which
  question or page · the value for "Set an answer".
-->
<script setup lang="ts">
import { actionTarget, LOGIC_ACTIONS, type LogicAction, type LogicEffect, type LogicValue } from '#shared/utils/forms/logic'

const props = defineProps<{ action: LogicEffect; index: number; removable: boolean }>()
const emit = defineEmits<{ update: [patch: Partial<LogicEffect>]; remove: [] }>()
const { t } = useI18n()
const logic = useLogicRules()

const actionItems = computed(() =>
  LOGIC_ACTIONS.map(a => ({
    value: a.action,
    label: t(`logic.action.${a.action}`),
    description: t(`logic.actionDesc.${a.action}`),
    icon: a.icon,
  })),
)
const kind = computed(() => actionTarget(props.action.action))
const targetItems = computed(() => logic.targetsFor(props.action.action))
const target = computed(() => logic.fieldById.value.get(props.action.target ?? ''))

function pickAction(next: LogicAction) {
  // A different kind of target (question ↔ page ↔ none) starts the target fresh.
  const same = actionTarget(next) === kind.value
  emit('update', {
    action: next,
    ...(same ? {} : { target: actionTarget(next) === 'none' ? undefined : '' }),
    ...(next === 'set_value' ? {} : { value: undefined }),
  })
}
</script>

<template>
  <div class="grid grid-cols-[minmax(0,1fr)_auto] gap-2 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1.8fr)_auto] sm:items-start">
    <USelectMenu
      :model-value="action.action"
      :items="actionItems"
      value-key="value"
      :icon="LOGIC_ACTIONS.find(a => a.action === action.action)?.icon"
      :search-input="false"
      :aria-label="t('logic.actionType', { n: index + 1 })"
      :ui="{ content: 'min-w-72' }"
      class="col-start-1 w-full sm:col-start-auto"
      @update:model-value="v => pickAction(v as LogicAction)"
    />
    <div class="col-start-1 flex min-w-0 flex-col gap-2 sm:col-start-auto">
      <USelectMenu
        v-if="kind !== 'none'"
        :model-value="action.target || undefined"
        :items="targetItems"
        value-key="value"
        :placeholder="kind === 'page' ? t('logic.pickPage') : t('logic.pickField')"
        :search-input="{ placeholder: t('common.search') }"
        :aria-label="t('logic.actionTarget', { n: index + 1 })"
        class="w-full"
        @update:model-value="v => v && emit('update', { target: String(v), ...(action.action === 'set_value' ? { value: null } : {}) })"
      />
      <p v-else class="px-1 py-1.5 text-xs text-muted">{{ t('logic.actionDesc.skip_to_end') }}</p>
      <FormsLogicValueInput
        v-if="action.action === 'set_value' && target"
        :field="target"
        op="set"
        :value="action.value"
        :label="t('logic.setValueFor', { field: logic.label(target) })"
        @update="(v: LogicValue) => emit('update', { value: v })"
      />
    </div>
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

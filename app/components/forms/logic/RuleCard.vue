<!--
  One rule as a card: "Rule 2" + problem badge + ⋯ menu (move up / down, duplicate, delete) in
  the header, the plain-language sentence below; "Edit" opens the When / Then editor in place.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { LogicCondition, LogicRule } from '#shared/utils/forms/logic'

const props = defineProps<{ rule: LogicRule; index: number; total: number }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const logic = useLogicRules()
const confirm = useConfirm()

const conditions = computed(() => logic.conditionsOf(props.rule))
const match = computed(() => logic.matchOf(props.rule))
const problem = computed(() => logic.problem(props.rule))
const group = (part: string) => `logic:${props.rule.id}:${part}`

function setMatch(next: string | number) {
  logic.update(props.rule.id, rule => {
    const list = rule.when.all ?? rule.when.any ?? []
    rule.when = next === 'any' ? { any: list } : { all: list }
  })
}
function editConditions(change: (list: LogicCondition[]) => void, part?: string) {
  logic.update(props.rule.id, rule => {
    const list = rule.when.any ?? rule.when.all ?? []
    change(list)
    rule.when = match.value === 'any' ? { any: list } : { all: list }
  }, part ? group(part) : undefined)
}
const updateCondition = (i: number, patch: Partial<LogicCondition>) =>
  editConditions(list => Object.assign(list[i]!, patch), `c${i}:${Object.keys(patch).join()}`)

async function remove() {
  if (await confirm({ title: t('logic.deleteTitle'), description: t('logic.deleteDesc'), danger: true, confirmLabel: t('logic.delete') }))
    logic.removeRule(props.rule.id)
}

const menu = computed<DropdownMenuItem[][]>(() => [
  [
    { label: t('logic.moveUp'), icon: 'i-lucide-arrow-up', disabled: props.index === 0, onSelect: () => logic.moveRule(props.rule.id, -1) },
    { label: t('logic.moveDown'), icon: 'i-lucide-arrow-down', disabled: props.index === props.total - 1, onSelect: () => logic.moveRule(props.rule.id, 1) },
    { label: t('logic.duplicate'), icon: 'i-lucide-copy', onSelect: () => logic.duplicateRule(props.rule.id) },
  ],
  [{ label: t('logic.delete'), icon: 'i-lucide-trash-2', color: 'error', onSelect: () => void remove() }],
])
</script>

<template>
  <UCard :ui="{ header: 'flex items-center gap-2 p-3 sm:px-4', body: 'p-3 sm:p-4' }">
    <template #header>
      <span class="flex size-7 shrink-0 items-center justify-center rounded-md border border-default">
        <UIcon name="i-lucide-git-branch" class="size-4 text-muted" />
      </span>
      <h3 class="truncate text-sm font-semibold text-highlighted">{{ t('logic.ruleN', { n: index + 1 }) }}</h3>
      <UBadge v-if="problem" :label="problem" icon="i-lucide-triangle-alert" color="warning" variant="subtle" size="sm" class="min-w-0 truncate rounded-md" />
      <div class="ms-auto flex shrink-0 items-center gap-1">
        <UButton
          :icon="open ? 'i-lucide-check' : 'i-lucide-pencil'"
          :label="open ? t('logic.done') : t('logic.edit')"
          color="neutral"
          variant="outline"
          size="sm"
          :aria-expanded="open"
          @click="open = !open"
        />
        <UDropdownMenu :items="menu" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="sm" square :aria-label="t('logic.menu', { n: index + 1 })" />
        </UDropdownMenu>
      </div>
    </template>

    <p class="text-sm text-default">{{ logic.summary(rule) }}</p>

    <div v-if="open" class="mt-4 flex flex-col gap-4 border-t border-default pt-4">
      <section class="flex flex-col gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <h4 class="text-xs font-medium text-muted uppercase">{{ t('logic.when') }}</h4>
          <UTabs
            v-if="conditions.length > 1"
            :model-value="match"
            :items="[{ value: 'all', label: t('logic.matchAll') }, { value: 'any', label: t('logic.matchAny') }]"
            :content="false"
            color="neutral"
            size="xs"
            :ui="SEGMENTED_UI"
            :aria-label="t('logic.match')"
            @update:model-value="setMatch"
          />
        </div>
        <FormsLogicConditionRow
          v-for="(condition, i) in conditions"
          :key="i"
          :condition="condition"
          :index="i"
          :removable="conditions.length > 1"
          @update="patch => updateCondition(i, patch)"
          @remove="editConditions(list => list.splice(i, 1))"
        />
        <UButton
          icon="i-lucide-plus"
          :label="t('logic.addCondition')"
          color="neutral"
          variant="ghost"
          size="sm"
          class="self-start"
          :disabled="conditions.length >= 20"
          @click="editConditions(list => list.push(logic.blankCondition()))"
        />
      </section>

      <section class="flex flex-col gap-2">
        <h4 class="text-xs font-medium text-muted uppercase">{{ t('logic.then') }}</h4>
        <FormsLogicActionRow
          v-for="(action, i) in rule.then"
          :key="i"
          :action="action"
          :index="i"
          :removable="rule.then.length > 1"
          @update="patch => logic.update(rule.id, r => Object.assign(r.then[i]!, patch))"
          @remove="logic.update(rule.id, r => r.then.splice(i, 1))"
        />
        <UButton
          icon="i-lucide-plus"
          :label="t('logic.addAction')"
          color="neutral"
          variant="ghost"
          size="sm"
          class="self-start"
          :disabled="rule.then.length >= 20"
          @click="logic.update(rule.id, r => r.then.push({ action: 'show', target: '' }))"
        />
      </section>
    </div>
  </UCard>
</template>

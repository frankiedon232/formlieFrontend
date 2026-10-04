<!--
  One rule as a card: "Rule 2" + problem badge + Edit + ⋯ (move, duplicate, delete) in the header;
  the plain-language sentence below. Edit opens two numbered steps, 1 IF (which answers to
  check) and 2 THEN (what happens), each with a short explanation, column labels and AND / OR
  between conditions, so anyone can follow it.
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
const problems = computed(() => logic.problems(props.rule))
const group = (part: string) => `logic:${props.rule.id}:${part}`

function setMatch(next: string | number) {
  logic.update(props.rule.id, rule => {
    const list = rule.when.all ?? rule.when.any ?? []
    rule.when = next === 'any' ? { any: list } : { all: list }
  })
}
function editConditions(change: (list: LogicCondition[]) => void, part?: string) {
  logic.update(
    props.rule.id,
    rule => {
      const list = rule.when.any ?? rule.when.all ?? []
      change(list)
      rule.when = match.value === 'any' ? { any: list } : { all: list }
    },
    part ? group(part) : undefined,
  )
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
      <UBadge
        v-if="problems.length"
        :label="problems.length > 1 ? t('logic.problemCount', { count: problems.length }, problems.length) : problems[0]"
        icon="i-lucide-triangle-alert"
        color="warning"
        variant="subtle"
        size="sm"
        class="min-w-0 truncate rounded-md"
      />
      <div class="ms-auto flex shrink-0 items-center gap-1">
        <UButton
          :icon="open ? 'i-lucide-check' : 'i-lucide-pencil'"
          :label="open ? t('logic.done') : t('logic.edit')"
          color="neutral"
          :variant="open ? 'solid' : 'outline'"
          size="sm"
          :aria-expanded="open"
          @click="open = !open"
        />
        <UDropdownMenu :items="menu" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="sm" square :aria-label="t('logic.menu', { n: index + 1 })" />
        </UDropdownMenu>
      </div>
    </template>

    <p class="flex items-start gap-2 rounded-md bg-elevated/50 px-3 py-2 text-sm text-default">
      <UIcon name="i-lucide-message-square-text" class="mt-0.5 size-4 shrink-0 text-muted" />
      <span>{{ logic.summary(rule) }}</span>
    </p>

    <ul v-if="problems.length > 1 || (open && problems.length)" class="mt-2 flex flex-col gap-1">
      <li v-for="p in problems" :key="p" class="flex items-center gap-1.5 text-xs text-warning">
        <UIcon name="i-lucide-triangle-alert" class="size-3.5 shrink-0" />{{ p }}
      </li>
    </ul>

    <div v-if="open" class="mt-4 flex flex-col gap-5">
      <!-- Step 1: IF -->
      <section class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
        <div class="flex flex-wrap items-center gap-2">
          <UBadge :label="t('logic.ifBadge')" color="neutral" variant="solid" class="rounded-md font-semibold" />
          <h4 class="text-sm font-semibold text-highlighted">{{ t('logic.ifTitle') }}</h4>
        </div>
        <p class="-mt-1 text-xs text-muted">{{ t('logic.ifHelp') }}</p>

        <div v-if="conditions.length > 1" class="flex flex-wrap items-center gap-2 text-sm">
          <span class="text-default">{{ t('logic.matchLead') }}</span>
          <UTabs
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

        <div class="hidden grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1.3fr)_2rem] gap-2 px-1 text-xs font-medium text-muted sm:grid">
          <span>{{ t('logic.colQuestion') }}</span>
          <span>{{ t('logic.colCondition') }}</span>
          <span>{{ t('logic.colAnswer') }}</span>
        </div>
        <template v-for="(condition, i) in conditions" :key="i">
          <div v-if="i > 0" class="flex items-center gap-2" aria-hidden="true">
            <span class="text-xs font-semibold text-muted uppercase">{{ match === 'any' ? t('logic.orChip') : t('logic.andChip') }}</span>
            <USeparator class="flex-1" />
          </div>
          <FormsLogicConditionRow
            :condition="condition"
            :index="i"
            :removable="conditions.length > 1"
            @update="patch => updateCondition(i, patch)"
            @remove="editConditions(list => list.splice(i, 1))"
          />
        </template>
        <UButton
          icon="i-lucide-plus"
          :label="t('logic.addCondition')"
          color="neutral"
          variant="outline"
          size="sm"
          class="self-start"
          :disabled="conditions.length >= 20"
          @click="editConditions(list => list.push(logic.blankCondition()))"
        />
      </section>

      <!-- Step 2: THEN -->
      <section class="flex flex-col gap-3 rounded-lg border border-default p-3 sm:p-4">
        <div class="flex flex-wrap items-center gap-2">
          <UBadge :label="t('logic.thenBadge')" color="neutral" variant="solid" class="rounded-md font-semibold" />
          <h4 class="text-sm font-semibold text-highlighted">{{ t('logic.thenTitle') }}</h4>
        </div>
        <p class="-mt-1 text-xs text-muted">{{ t('logic.thenHelp') }}</p>
        <div class="hidden grid-cols-[minmax(0,1.2fr)_minmax(0,1.8fr)_2rem] gap-2 px-1 text-xs font-medium text-muted sm:grid">
          <span>{{ t('logic.colAction') }}</span>
          <span>{{ t('logic.colTarget') }}</span>
        </div>
        <FormsLogicActionRow
          v-for="(action, i) in rule.then"
          :key="i"
          :action="action"
          :index="i"
          :removable="rule.then.length > 1"
          @update="patch => logic.update(rule.id, r => Object.assign(r.then[i]!, patch), group(`a${i}:${Object.keys(patch).join()}`))"
          @remove="logic.update(rule.id, r => r.then.splice(i, 1))"
        />
        <UButton
          icon="i-lucide-plus"
          :label="t('logic.addAction')"
          color="neutral"
          variant="outline"
          size="sm"
          class="self-start"
          :disabled="rule.then.length >= 20"
          @click="logic.update(rule.id, r => r.then.push({ action: 'show', target: '' }))"
        />
      </section>
    </div>
  </UCard>
</template>

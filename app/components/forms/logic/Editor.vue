<!--
  Body of the logic page. Lives below <FormsBuilderFrame> so it can inject the builder that the
  page's session provides. Rules column + calculations card.
-->
<script setup lang="ts">
import { LOGIC_ACTIONS, type LogicAction } from '#shared/utils/forms/logic'

const { t } = useI18n()
const logic = useLogicRules()
const openId = ref<string | null>(null)

const problems = computed(() => logic.rules.value.filter(rule => logic.problem(rule)).length)
const canAdd = computed(() => logic.sources.value.length > 0 && logic.rules.value.length < 500)

function add(preset: LogicAction = 'show') {
  openId.value = logic.addRule(preset)
}
// Starting points shown when there are no rules yet.
const starters = computed(() =>
  (['show', 'require', 'jump', 'set_value'] as LogicAction[])
    .filter(action => action !== 'jump' || logic.pages.value.length > 1)
    .map(action => ({
      action,
      icon: LOGIC_ACTIONS.find(a => a.action === action)!.icon,
      title: t(`logic.starter.${action}.title`),
      text: t(`logic.starter.${action}.text`),
    })),
)

defineShortcuts({ n: { handler: () => canAdd.value && add(), usingInput: false } })
</script>

<template>
  <div class="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
    <UCard :ui="{ header: 'flex flex-wrap items-center gap-2 p-3 sm:px-4', body: 'flex flex-col gap-3 p-3 sm:p-4 bg-elevated/40' }">
      <template #header>
        <h2 class="text-sm font-semibold text-highlighted">{{ t('logic.rules') }}</h2>
        <UBadge :label="String(logic.rules.value.length)" color="neutral" variant="outline" size="sm" class="rounded-md" />
        <UBadge
          v-if="problems"
          :label="t('logic.problems', { count: problems })"
          icon="i-lucide-triangle-alert"
          color="warning"
          variant="subtle"
          size="sm"
          class="rounded-md"
        />
        <UButton
          icon="i-lucide-plus"
          :label="t('logic.add')"
          data-help="logic-add"
          color="neutral"
          size="sm"
          class="ms-auto"
          :disabled="!canAdd"
          @click="add()"
        >
          <template #trailing><UKbd value="N" class="hidden sm:inline-flex" /></template>
        </UButton>
      </template>

      <AppEmpty
        v-if="!logic.sources.value.length"
        icon="i-lucide-layout-panel-top"
        :title="t('logic.noFieldsTitle')"
        :description="t('logic.noFieldsDesc')"
        :actions="[{ label: t('builder.mode.build'), icon: 'i-lucide-layout-panel-top', color: 'neutral', to: `/forms/${$route.params.id}/build` }]"
        variant="naked"
        class="py-10"
      />
      <div v-else-if="!logic.rules.value.length" class="flex flex-col gap-4 py-4">
        <AppEmpty size="sm" icon="i-lucide-git-branch" :title="t('logic.emptyTitle')" :description="t('logic.emptyDesc')" class="min-h-0 py-2" />
        <div class="grid gap-2 sm:grid-cols-2">
          <UButton
            v-for="starter in starters"
            :key="starter.action"
            color="neutral"
            variant="outline"
            class="items-start gap-3 bg-default p-3 text-start"
            @click="add(starter.action)"
          >
            <span class="flex size-8 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50">
              <UIcon :name="starter.icon" class="size-4 text-highlighted" />
            </span>
            <span class="flex min-w-0 flex-col">
              <span class="text-sm font-medium text-highlighted">{{ starter.title }}</span>
              <span class="text-xs font-normal text-muted">{{ starter.text }}</span>
            </span>
          </UButton>
        </div>
      </div>
      <FormsLogicRuleCard
        v-for="(rule, i) in logic.rules.value"
        :key="rule.id"
        :rule="rule"
        :index="i"
        :total="logic.rules.value.length"
        :open="openId === rule.id"
        @update:open="v => (openId = v ? rule.id : null)"
      />
    </UCard>

    <div class="flex flex-col gap-4 lg:sticky lg:top-0">
      <FormsLogicCalculations data-help="logic-calculations" />
      <UAlert icon="i-lucide-lightbulb" color="neutral" variant="outline" :title="t('logic.tipTitle')" :description="t('logic.tipDesc')" />
    </div>
  </div>
</template>

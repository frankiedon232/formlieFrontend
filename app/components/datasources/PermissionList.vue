<!--
  Every operation Formalie performs on this database, grouped by level (Formalie's tables, always;
  reading and changing the other tables, optional), with what it is used for and the privilege
  behind it on this engine. Without test results it
  marks what this connection needs; with them (a finished test) each line says granted or missing.
-->
<script setup lang="ts">
import type { DataSourceAccessSettings, DbEngine, PermissionResult } from '#shared/types/datasources'
import { operationsFor, type PermissionLevel } from '#shared/utils/datasources/permissions'

const props = defineProps<{ engine: DbEngine; access: DataSourceAccessSettings; results?: PermissionResult[] | null }>()
const { t } = useI18n()

const LEVELS: PermissionLevel[] = ['own', 'read', 'write']
const groups = computed(() => {
  const operations = operationsFor(props.engine, props.access)
  const result = (key: string) => props.results?.find(item => item.operation === key)?.status
  return LEVELS.map(level => ({
    level,
    needed: operations.some(op => op.level === level && op.needed),
    items: operations.filter(op => op.level === level).map(op => ({ ...op, result: result(op.key) })),
  }))
})
const STATE = {
  granted: { icon: 'i-lucide-circle-check', class: 'text-success' },
  missing: { icon: 'i-lucide-circle-x', class: 'text-error' },
  needed: { icon: 'i-lucide-circle-dot', class: 'text-highlighted' },
  not_needed: { icon: 'i-lucide-circle-minus', class: 'text-dimmed' },
}
const stateOf = (item: { needed: boolean; result?: string }) => (item.result === 'granted' || item.result === 'missing' ? item.result : item.needed ? 'needed' : 'not_needed')
</script>

<template>
  <div class="flex flex-col gap-3">
    <section v-for="group in groups" :key="group.level" class="rounded-lg border border-default" :class="group.needed ? '' : 'opacity-60'">
      <header class="flex items-center justify-between gap-2 border-b border-default px-3 py-2">
        <div class="flex min-w-0 flex-col">
          <h4 class="text-sm font-semibold text-highlighted">{{ t(`dataSources.level.${group.level}`) }}</h4>
          <p class="text-xs text-muted">{{ t(`dataSources.levelDesc.${group.level}`) }}</p>
        </div>
        <UBadge :label="group.level === 'own' ? t('dataSources.access.always') : group.needed ? t('dataSources.perm.needed') : t('dataSources.perm.notNeeded')" color="neutral" :variant="group.needed ? 'solid' : 'outline'" size="sm" class="shrink-0 rounded-md" />
      </header>
      <ul class="divide-y divide-default">
        <li v-for="item in group.items" :key="item.key" class="flex items-start gap-2.5 px-3 py-2">
          <UIcon :name="item.icon" class="mt-0.5 size-4 shrink-0 text-muted" />
          <div class="flex min-w-0 flex-1 flex-col gap-0.5">
            <span class="text-sm text-highlighted">{{ t(`dataSources.op.${item.key}.label`) }}</span>
            <span class="text-xs text-muted">{{ t(`dataSources.op.${item.key}.uses`) }}</span>
            <code class="w-fit rounded bg-elevated px-1.5 py-0.5 font-mono text-[11px] text-toned" dir="ltr">{{ item.privilege }}</code>
          </div>
          <UTooltip :text="t(`dataSources.perm.${stateOf(item)}`)">
            <UIcon :name="STATE[stateOf(item)].icon" class="mt-0.5 size-4 shrink-0" :class="STATE[stateOf(item)].class" :aria-label="t(`dataSources.perm.${stateOf(item)}`)" />
          </UTooltip>
        </li>
      </ul>
    </section>
  </div>
</template>

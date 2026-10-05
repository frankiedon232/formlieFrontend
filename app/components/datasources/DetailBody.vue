<!--
  Connection panel body (F12, detail panel model): fact tiles; chips to show one group (All ·
  Connection · Security · Permissions · Health) in a sliding row; settings as two-column tiles of
  equal height (secrets only say whether they are saved and when they changed); permissions with
  the last test's result per operation, its advice and the statements to grant what is missing;
  uptime for 30 days and the latest health checks (every five minutes).
-->
<script setup lang="ts">
import type { DataSourceDetail } from '#shared/types/datasources'
import { fieldsFor, isSecretField, type EngineField } from '#shared/utils/datasources/engines'

const props = defineProps<{ source: DataSourceDetail }>()
const { t } = useI18n()
const { relative, dateTime, number } = useFormat()

type Group = 'all' | 'connection' | 'security' | 'permissions' | 'health'
const group = ref<Group>('all')
const GROUPS: { key: Group; icon: string }[] = [
  { key: 'all', icon: 'i-lucide-layout-grid' },
  { key: 'connection', icon: 'i-lucide-server' },
  { key: 'security', icon: 'i-lucide-lock' },
  { key: 'permissions', icon: 'i-lucide-key-round' },
  { key: 'health', icon: 'i-lucide-heart-pulse' },
]
const show = (key: Group) => group.value === 'all' || group.value === key

const facts = computed(() => [
  { label: t('dataSources.kpi.latency'), value: props.source.latency_ms === null ? '–' : t('dataSources.ms', { n: props.source.latency_ms }) },
  { label: t('dataSources.uptime'), value: props.source.uptime_30d === null ? '–' : `${props.source.uptime_30d}%` },
  { label: t('dataSources.lastChecked'), value: props.source.last_checked_at ? relative(props.source.last_checked_at) : '–' },
  { label: t('dataSources.kpi.operations'), value: number(props.source.operations_30d) },
  { label: t('dataSources.formsUsing'), value: number(props.source.forms_count) },
  { label: t('dataSources.addedBy'), value: props.source.created_by.name },
])

const valueOf = (field: EngineField) => {
  const value = props.source.settings[field.key]
  if (field.type === 'switch') return value ? t('dataSources.yes') : t('dataSources.no')
  if (field.type === 'select') return t(`dataSources.option.${field.key}.${value}`)
  return value === '' || value === undefined ? '–' : String(value)
}
const tiles = (steps: string[]) =>
  fieldsFor(props.source.engine, props.source.settings)
    .filter(field => steps.includes(field.step))
    .map(field => ({
      key: field.key,
      label: t(`dataSources.field.${field.key}`),
      value: isSecretField(field) ? (props.source.secrets_set.includes(field.key) ? t('dataSources.secretSaved') : t('dataSources.secretNotSet')) : valueOf(field),
      secret: isSecretField(field),
      ltr: !isSecretField(field) && field.type === 'text',
    }))
const connectionTiles = computed(() => tiles(['server', 'signin']))
const securityTiles = computed(() => tiles(['security']))
const uptimeDays = computed(() => props.source.uptime_daily.map(day => ({ date: day.date, count: day.uptime ?? 0 })))
const CHECK = { passed: { icon: 'i-lucide-circle-check', class: 'text-success' }, warning: { icon: 'i-lucide-triangle-alert', class: 'text-warning' }, failed: { icon: 'i-lucide-circle-x', class: 'text-error' } }
const scriptOpen = ref(false)
</script>

<template>
  <div class="flex flex-col gap-5">
    <dl class="grid grid-cols-2 gap-2 sm:grid-cols-3">
      <div v-for="fact in facts" :key="fact.label" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="truncate text-sm font-medium text-highlighted tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <AppChipScroller :label="t('dataSources.detail.groups')">
      <button
        v-for="item in GROUPS"
        :key="item.key"
        type="button"
        data-chip
        :aria-pressed="group === item.key"
        class="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
        :class="group === item.key ? 'bg-default text-highlighted shadow-xs ring-1 ring-(--ui-border)' : 'text-muted hover:text-highlighted'"
        @click="group = item.key"
      >
        <UIcon :name="item.icon" class="size-3.5" />
        {{ t(`dataSources.detail.${item.key}`) }}
      </button>
    </AppChipScroller>

    <section v-for="part in [{ key: 'connection' as const, tiles: connectionTiles }, { key: 'security' as const, tiles: securityTiles }]" v-show="show(part.key)" :key="part.key" class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t(`dataSources.detail.${part.key}`) }}</h3>
      <dl class="grid auto-rows-fr grid-cols-1 gap-2 sm:grid-cols-2">
        <div v-for="tile in part.tiles" :key="tile.key" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
          <dt class="truncate text-[11px] text-muted">{{ tile.label }}</dt>
          <dd class="flex min-w-0 items-center gap-1.5 text-sm text-highlighted">
            <UIcon v-if="tile.secret" name="i-lucide-key-round" class="size-3.5 shrink-0 text-muted" />
            <span class="truncate" :class="tile.ltr ? 'text-start font-mono text-xs' : ''" :dir="tile.ltr ? 'ltr' : undefined">{{ tile.value }}</span>
          </dd>
        </div>
      </dl>
      <p v-if="part.key === 'security' && source.secrets_changed_at" class="text-xs text-muted">{{ t('dataSources.secretsChanged', { when: dateTime(source.secrets_changed_at) }) }}</p>
      <DatasourcesEgressIps v-if="part.key === 'security'" />
    </section>

    <section v-show="show('permissions')" class="flex flex-col gap-2">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('dataSources.detail.permissions') }}</h3>
      <p class="text-xs text-muted">{{ source.last_test?.finished_at ? t('dataSources.detail.permissionsFrom', { when: relative(source.last_test.finished_at) }) : t('dataSources.detail.permissionsUntested') }}</p>
      <UAlert v-for="finding in source.last_test?.findings ?? []" :key="finding" :icon="finding === 'missing_permissions' ? 'i-lucide-key-round' : 'i-lucide-shield-alert'" color="warning" variant="subtle" :title="t(`dataSources.finding.${finding}.title`)" :description="t(`dataSources.finding.${finding}.desc`)" />
      <DatasourcesPermissionList :engine="source.engine" :access="source.access" :results="source.last_test?.permissions" />
      <UCollapsible v-model:open="scriptOpen" class="flex flex-col gap-2">
        <UButton :label="t('dataSources.detail.howToGrant')" icon="i-lucide-square-terminal" :trailing-icon="scriptOpen ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'" color="neutral" variant="outline" size="sm" class="w-fit" />
        <template #content>
          <DatasourcesGrantScript :engine="source.engine" :settings="source.settings" :access="source.access" />
        </template>
      </UCollapsible>
    </section>

    <section v-show="show('health')" class="flex flex-col gap-3">
      <h3 class="text-xs font-semibold tracking-wide text-muted uppercase">{{ t('dataSources.detail.health') }}</h3>
      <div class="rounded-lg border border-default p-3">
        <ChartsMiniBars :days="uptimeDays" :label="t('dataSources.uptimePercent')" height="h-16" />
      </div>
      <ul v-if="source.checks.length" class="divide-y divide-default rounded-lg border border-default">
        <li v-for="check in source.checks" :key="check.at" class="flex items-center gap-2.5 px-3 py-2 text-sm">
          <UIcon :name="CHECK[check.status].icon" class="size-4 shrink-0" :class="CHECK[check.status].class" />
          <UTooltip :text="dateTime(check.at)"><span class="text-default">{{ relative(check.at) }}</span></UTooltip>
          <span v-if="check.error_code" class="min-w-0 flex-1 truncate text-xs text-muted">{{ t(`errors.${check.error_code}`) }}</span>
          <span class="ms-auto text-xs text-muted tabular-nums">{{ check.latency_ms === null ? '–' : t('dataSources.ms', { n: check.latency_ms }) }}</span>
        </li>
      </ul>
      <p v-else class="text-sm text-muted">{{ t('dataSources.detail.noChecks') }}</p>
    </section>
  </div>
</template>

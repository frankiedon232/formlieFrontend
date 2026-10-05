<!--
  A connection test as it runs (F12 M1): a percentage bar, then each step (reach the server, SSH
  tunnel, encryption, sign in, open the database, check permissions) with its state and time. A
  failed step says what went wrong and how to fix it. When finished: server version, response
  time, schemas and tables found, and advice (administrator account, unencrypted traffic, more
  rights than needed). The test never changes data.
-->
<script setup lang="ts">
import type { ConnectionTest, TestStepStatus } from '#shared/types/datasources'

const props = defineProps<{ test: ConnectionTest | null; starting?: boolean }>()
const { t, te } = useI18n()
const { number } = useFormat()

const STATE: Record<TestStepStatus, { icon: string; class: string }> = {
  pending: { icon: 'i-lucide-circle', class: 'text-dimmed' },
  running: { icon: 'i-lucide-loader-circle', class: 'animate-spin text-highlighted' },
  passed: { icon: 'i-lucide-circle-check', class: 'text-success' },
  warning: { icon: 'i-lucide-triangle-alert', class: 'text-warning' },
  failed: { icon: 'i-lucide-circle-x', class: 'text-error' },
  skipped: { icon: 'i-lucide-circle-minus', class: 'text-dimmed' },
}
const steps = computed(() => props.test?.steps ?? [])
const percent = computed(() => {
  if (!props.test) return props.starting ? 3 : 0
  const counted = steps.value.filter(step => step.status !== 'skipped' || props.test!.status === 'running')
  const done = counted.filter(step => !['pending', 'running'].includes(step.status)).length
  return props.test.status === 'running' ? Math.max(5, Math.round((done / Math.max(1, counted.length)) * 100)) : 100
})
const facts = computed(() => {
  const test = props.test
  if (!test || test.status === 'running' || test.status === 'failed') return []
  return [
    { label: t('dataSources.test.version'), value: test.server_version ?? '–' },
    { label: t('dataSources.test.latency'), value: test.latency_ms === null ? '–' : t('dataSources.ms', { n: test.latency_ms }) },
    { label: t('dataSources.test.schemas'), value: number(test.schemas.length) },
    { label: t('dataSources.test.tables'), value: test.tables_count === null ? '–' : number(test.tables_count) },
  ]
})
const fixFor = (code: string | null) => (code && te(`dataSources.fix.${code}`) ? t(`dataSources.fix.${code}`) : null)
const heading = computed(() => (!props.test ? 'running' : props.test.status))
</script>

<template>
  <div class="flex flex-col gap-4" :aria-busy="!test || test.status === 'running' || undefined">
    <div class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2 text-sm">
        <span class="font-medium text-highlighted" role="status">{{ t(`dataSources.test.heading.${heading}`) }}</span>
        <span class="text-muted tabular-nums">{{ percent }}%</span>
      </div>
      <UProgress :model-value="percent" color="neutral" size="sm" />
    </div>

    <ol class="flex flex-col">
      <li v-for="step in steps" :key="step.key" class="flex gap-3 py-1.5">
        <UIcon :name="STATE[step.status].icon" class="mt-0.5 size-4 shrink-0" :class="STATE[step.status].class" />
        <div class="flex min-w-0 flex-1 flex-col gap-0.5">
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm" :class="step.status === 'pending' || step.status === 'skipped' ? 'text-muted' : 'text-highlighted'">{{ t(`dataSources.step.${step.key}`) }}</span>
            <span v-if="step.duration_ms !== null" class="text-xs text-muted tabular-nums">{{ t('dataSources.ms', { n: step.duration_ms }) }}</span>
            <span v-else-if="step.status === 'skipped'" class="text-xs text-dimmed">{{ t('dataSources.test.skipped') }}</span>
          </div>
          <p v-if="step.status === 'running'" class="text-xs text-muted">{{ t(`dataSources.stepDesc.${step.key}`) }}</p>
          <p v-if="step.key === 'tls' && step.status === 'warning'" class="text-xs text-warning">{{ t('dataSources.test.tlsOff') }}</p>
          <div v-if="step.error_code && (step.status === 'failed' || step.status === 'warning')" class="mt-1 flex flex-col gap-1 rounded-md border px-2.5 py-2 text-xs" :class="step.status === 'failed' ? 'border-error/30 bg-error/5' : 'border-warning/30 bg-warning/5'">
            <span class="font-medium" :class="step.status === 'failed' ? 'text-error' : 'text-warning'">{{ t(`errors.${step.error_code}`) }}</span>
            <span v-if="fixFor(step.error_code)" class="text-default">{{ fixFor(step.error_code) }}</span>
          </div>
        </div>
      </li>
      <template v-if="!test">
        <li v-for="n in 5" :key="n" class="flex items-center gap-3 py-1.5"><USkeleton class="size-4 rounded-full" /><USkeleton class="h-4 w-40" /></li>
      </template>
    </ol>

    <dl v-if="facts.length" class="grid grid-cols-2 gap-2 sm:grid-cols-4">
      <div v-for="fact in facts" :key="fact.label" class="flex min-w-0 flex-col gap-0.5 rounded-lg border border-default px-3 py-2">
        <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
        <dd class="truncate text-sm font-medium text-highlighted tabular-nums" dir="ltr">{{ fact.value }}</dd>
      </div>
    </dl>

    <ul v-if="test && test.findings.length" class="flex flex-col gap-2">
      <li v-for="finding in test.findings" :key="finding">
        <UAlert :icon="finding === 'missing_permissions' ? 'i-lucide-key-round' : 'i-lucide-shield-alert'" color="warning" variant="subtle" :title="t(`dataSources.finding.${finding}.title`)" :description="t(`dataSources.finding.${finding}.desc`)" />
      </li>
    </ul>

    <p class="flex items-center gap-1.5 text-xs text-muted">
      <UIcon name="i-lucide-shield-check" class="size-3.5 shrink-0" />
      {{ t('dataSources.test.safe') }}
    </p>
  </div>
</template>

<!--
  Last step: a name, a summary of the connection (each line jumps back to its step) and the test.
  Testing is the way to save with confidence; a failed step offers "Fix" on the step it belongs to.
-->
<script setup lang="ts">
import type { ConnectionTest, DataSourceAccessSettings, DataSourceSettings, TestStepKey } from '#shared/types/datasources'
import type { DbEngine } from '#shared/utils/integrations/databases'
import { addressOf, databaseNameOf, isEncrypted } from '#shared/utils/datasources/engines'
import { tablesSchemaOf } from '#shared/utils/datasources/permissions'

const props = defineProps<{ engine: DbEngine; settings: DataSourceSettings; access: DataSourceAccessSettings; test: ConnectionTest | null; starting: boolean; running: boolean; nameError?: string }>()
const name = defineModel<string>('name', { required: true })
const emit = defineEmits<{ test: []; jump: [step: string] }>()
const { t } = useI18n()

const rows = computed(() => [
  { key: 'engine', step: 'engine', icon: engineIcon(props.engine), label: t('dataSources.summary.engine'), value: engineName(props.engine) },
  { key: 'address', step: 'server', icon: 'i-lucide-server', label: t('dataSources.summary.address'), value: addressOf(props.engine, props.settings) || t('dataSources.summary.descriptor'), ltr: true },
  { key: 'database', step: 'server', icon: 'i-lucide-database', label: t('dataSources.summary.database'), value: databaseNameOf(props.engine, props.settings), ltr: true },
  { key: 'account', step: 'signin', icon: 'i-lucide-user-round', label: t('dataSources.summary.account'), value: String(props.settings.username || props.settings.client_id || ''), ltr: true },
  { key: 'security', step: 'security', icon: isEncrypted(props.engine, props.settings) ? 'i-lucide-lock' : 'i-lucide-lock-open', label: t('dataSources.summary.security'), value: [isEncrypted(props.engine, props.settings) ? t('dataSources.summary.encrypted') : t('dataSources.summary.notEncrypted'), props.settings.ssh ? t('dataSources.summary.ssh') : null].filter(Boolean).join(' · ') },
  { key: 'tables', step: 'access', icon: 'i-lucide-inbox', label: t('dataSources.summary.tables'), value: `${tablesSchemaOf(props.engine, props.settings, props.access)}.${props.access.table_prefix}…`, ltr: true },
  { key: 'access', step: 'access', icon: OTHER_ICON[props.access.other], label: t('dataSources.summary.access'), value: t(`dataSources.access.other.${props.access.other}`) },
])
const STEP_OF: Record<TestStepKey, string> = { network: 'server', ssh: 'security', tls: 'security', sign_in: 'signin', database: 'server', permissions: 'access' }
const failedStep = computed(() => props.test?.steps.find(step => step.status === 'failed' || (step.key === 'permissions' && step.status === 'warning')))
</script>

<template>
  <div class="flex flex-col gap-5">
    <UFormField :label="t('dataSources.wizard.name')" :description="t('dataSources.wizard.nameDesc')" name="name" :error="nameError" required>
      <UInput v-model="name" maxlength="80" class="w-full" :placeholder="t('dataSources.wizard.namePlaceholder')" />
    </UFormField>

    <dl class="grid grid-cols-1 gap-2 sm:grid-cols-2">
      <button
        v-for="row in rows"
        :key="row.key"
        type="button"
        class="flex min-w-0 items-center gap-2.5 rounded-lg border border-default px-3 py-2 text-start transition hover:border-accented hover:bg-elevated/40 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
        :aria-label="t('dataSources.summary.change', { item: row.label })"
        @click="emit('jump', row.step)"
      >
        <UIcon :name="row.icon" class="size-4 shrink-0 text-muted" />
        <span class="flex min-w-0 flex-1 flex-col">
          <dt class="text-[11px] text-muted">{{ row.label }}</dt>
          <dd class="truncate text-sm font-medium text-highlighted" :dir="row.ltr ? 'ltr' : undefined" :class="row.ltr ? 'text-start' : ''">{{ row.value || '–' }}</dd>
        </span>
        <UIcon name="i-lucide-pencil" class="size-3.5 shrink-0 text-dimmed" />
      </button>
    </dl>

    <div class="flex flex-col gap-4 rounded-lg border border-default p-3 sm:p-4">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex min-w-0 flex-col">
          <h3 class="text-sm font-semibold text-highlighted">{{ t('dataSources.wizard.testTitle') }}</h3>
          <p class="text-xs text-muted">{{ t('dataSources.wizard.testDesc') }}</p>
        </div>
        <UButton :label="test && !running ? t('dataSources.wizard.testAgain') : t('dataSources.wizard.test')" icon="i-lucide-activity" color="neutral" :variant="test && !running ? 'outline' : 'solid'" :loading="starting || running" @click="emit('test')" />
      </div>
      <DatasourcesTestProgress v-if="test || starting" :test="test" :starting="starting" />
      <UButton v-if="failedStep && !running" :label="t('dataSources.wizard.fixStep', { step: t(`dataSources.step.${failedStep.key}`) })" icon="i-lucide-wrench" color="neutral" variant="outline" size="sm" class="w-fit" @click="emit('jump', STEP_OF[failedStep.key])" />
    </div>
  </div>
</template>

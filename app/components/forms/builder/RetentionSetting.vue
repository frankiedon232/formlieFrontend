<!--
  Form settings → Keep responses (F14 M5): how long this form's responses are kept before they are
  removed for good; the workspace's choice (Settings → Privacy and data) unless the form sets its own.
  Applies once published.
-->
<script setup lang="ts">
import { RETENTION_DAYS } from '#shared/types/privacy'

const { t } = useI18n()
const builder = useBuilder()
const schema = builder.schema
const store = useWorkspaceSettings()
// Admins see the workspace's choice; members just "the workspace's"
onMounted(() => useCan().can('settings.view') && void store.load().catch(() => {}))

const WORKSPACE = -1
const label = (days: number) => (days ? t('builder.retention.days', { n: days }, days) : t('builder.retention.keep'))
const workspaceDays = computed(() => store.settings.value?.privacy.retention_days ?? null)
const items = computed(() => [
  { value: WORKSPACE, label: workspaceDays.value === null ? t('builder.retention.workspace') : t('builder.retention.workspaceIs', { value: label(workspaceDays.value) }) },
  ...RETENTION_DAYS.map(days => ({ value: days, label: label(days) })),
])
const current = computed(() => (schema.value?.settings as { retention_days?: number | null } | undefined)?.retention_days ?? WORKSPACE)
function update(value: number) {
  if (!schema.value) return
  builder.history.record()
  const { retention_days: _old, ...rest } = (schema.value.settings ?? {}) as Record<string, unknown>
  schema.value.settings = value === WORKSPACE ? rest : { ...rest, retention_days: value }
}
</script>

<template>
  <section class="flex flex-col gap-3">
    <h3 class="text-xs font-medium text-muted uppercase">{{ t('builder.retention.title') }}</h3>
    <UFormField :description="t('builder.retention.hint')">
      <USelect :model-value="current" :items="items" icon="i-lucide-calendar-x" class="w-full" :aria-label="t('builder.retention.title')" @update:model-value="value => update(Number(value))" />
    </UFormField>
  </section>
</template>

<!--
  Where this form's responses are stored (F12 M2), on the form's overview: Formalie's encrypted
  storage (the default, with "Store in your database"), or the connection and table with the last
  30 days of deliveries, anything pending or failed, and new fields that have no column yet.
-->
<script setup lang="ts">
import type { FormStorage } from '#shared/types/destinations'

const props = defineProps<{ formId: string }>()
const { t } = useI18n()
const api = useApi()
const { number, relative } = useFormat()
const storage = ref<(FormStorage & { can_manage: boolean }) | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    storage.value = (await api.get<FormStorage & { can_manage: boolean }>(`/forms/${props.formId}/storage`, undefined, { background: true })).data
  } catch {
    failed.value = true
  }
}
onMounted(load)
const destination = computed(() => storage.value?.destination ?? null)
const facts = computed(() =>
  destination.value
    ? [
        { label: t('destinations.kpi.sent30'), value: number(destination.value.sent_30d) },
        { label: t('destinations.kpi.pending'), value: number(destination.value.pending) },
        { label: t('destinations.kpi.failed'), value: number(destination.value.failed), warn: destination.value.failed > 0 },
      ]
    : [],
)
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-5' }">
    <div class="flex items-center justify-between gap-2">
      <h2 class="text-sm font-semibold text-highlighted">{{ t('destinations.card.title') }}</h2>
      <DataStatusBadge v-if="destination" :status="destination.status" :label="t(`destinations.status.${destination.status}`)" />
    </div>

    <div v-if="!storage && !failed" class="flex flex-col gap-2"><USkeleton class="h-10 w-full" /><USkeleton class="h-8 w-2/3" /></div>
    <p v-else-if="failed" class="text-sm text-muted">
      {{ t('dataView.errorTitle') }}
      <UButton :label="t('common.retry')" color="neutral" variant="link" size="xs" @click="load" />
    </p>

    <!-- Formalie's storage -->
    <template v-else-if="storage && !destination">
      <div class="flex items-start gap-3">
        <span class="flex size-10 shrink-0 items-center justify-center rounded-lg border border-default"><UIcon name="i-lucide-shield-check" class="size-5 text-highlighted" /></span>
        <div class="flex min-w-0 flex-col">
          <span class="text-sm font-medium text-highlighted">{{ t('destinations.card.formalie') }}</span>
          <span class="text-xs text-muted">{{ t('destinations.card.formalieDesc') }}</span>
        </div>
      </div>
      <template v-if="storage.can_manage">
        <UButton v-if="storage.connections" :label="t('destinations.card.store')" icon="i-lucide-database" color="neutral" variant="outline" size="sm" class="w-fit" :to="`/forms/${formId}/storage`" />
        <UButton v-else :label="t('destinations.card.addConnection')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" class="w-fit" to="/data-sources/connections/new" />
      </template>
    </template>

    <!-- A database -->
    <template v-else-if="destination">
      <NuxtLink :to="{ path: '/data-sources/destinations', query: { destination: destination.id } }" class="flex items-start gap-3 rounded-lg focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)">
        <DatasourcesEngineLogo :engine="destination.datasource.engine" />
        <div class="flex min-w-0 flex-col">
          <span class="truncate text-sm font-medium text-highlighted">{{ destination.datasource.name }}</span>
          <code class="truncate text-start font-mono text-xs text-muted" dir="ltr">{{ destination.table.schema }}.{{ destination.table.name }}</code>
        </div>
      </NuxtLink>
      <dl class="grid grid-cols-3 gap-2">
        <div v-for="fact in facts" :key="fact.label" class="flex min-w-0 flex-col rounded-lg border border-default px-2.5 py-1.5">
          <dt class="truncate text-[11px] text-muted">{{ fact.label }}</dt>
          <dd class="text-sm font-medium tabular-nums" :class="fact.warn ? 'text-error' : 'text-highlighted'">{{ fact.value }}</dd>
        </div>
      </dl>
      <p class="text-xs text-muted">{{ destination.last_delivery_at ? t('destinations.card.last', { when: relative(destination.last_delivery_at) }) : t('destinations.card.none') }}</p>
      <UAlert v-if="destination.new_fields" icon="i-lucide-columns-3" color="warning" variant="subtle" :title="t('destinations.card.newFields', { n: destination.new_fields }, destination.new_fields)" />
      <div v-if="storage?.can_manage" class="flex flex-wrap gap-2">
        <UButton :label="t('destinations.card.open')" icon="i-lucide-panel-right-open" color="neutral" variant="outline" size="sm" :to="{ path: '/data-sources/destinations', query: { destination: destination.id } }" />
        <UButton :label="t('destinations.card.change')" icon="i-lucide-pencil" color="neutral" variant="ghost" size="sm" :to="`/forms/${formId}/storage`" />
      </div>
    </template>
  </UCard>
</template>

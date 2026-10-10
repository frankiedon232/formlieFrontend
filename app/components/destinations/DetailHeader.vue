<!--
  Destination panel header (detail panel model): the form, the connection and table, badges,
  ⋯ (open the form, open the connection, change columns, copy link, back to Formalie's storage)
  and close; then the one-click bar: Delivering on / off, Send earlier responses, Retry failed.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DestinationDetail } from '#shared/types/destinations'

const props = defineProps<{ destination: DestinationDetail; busy: boolean }>()
const emit = defineEmits<{ pause: [paused: boolean]; backfill: []; retry: []; remove: []; close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })
// Changing how the form is stored needs data.storage
const { can } = useCan()
const running = computed(() => props.destination.backfill?.status === 'running')
const menu = computed<DropdownMenuItem[][]>(() =>
  [
    [
      { label: t('destinations.actions.openForm'), icon: 'i-lucide-file-text', to: `/forms/${props.destination.form.id}` },
      { label: t('destinations.actions.openConnection'), icon: 'i-lucide-database', to: { path: '/data-sources/connections', query: { connection: props.destination.datasource.id } } },
      ...(can('data.storage') ? [{ label: t('destinations.actions.change'), icon: 'i-lucide-columns-3', to: `/forms/${props.destination.form.id}/storage` }] : []),
      {
        label: t('dataSources.actions.copyLink'),
        icon: 'i-lucide-link',
        onSelect: () => {
          void copy(`${location.origin}/data-sources/destinations?destination=${props.destination.id}`)
          toast.add({ title: t('dataSources.toast.linkCopied'), color: 'success', icon: 'i-lucide-check' })
        },
      },
    ],
    can('data.storage') ? [{ label: t('destinations.actions.remove'), icon: 'i-lucide-undo-2', color: 'error' as const, onSelect: () => emit('remove') }] : [],
  ].filter(group => group.length),
)
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <div class="flex items-start gap-3.5">
      <DatasourcesEngineLogo :engine="destination.datasource.engine" size="lg" />
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ destination.form.name }}</h2>
        <p class="truncate text-sm text-muted">
          {{ destination.datasource.name }} ·
          <code class="font-mono text-xs" dir="ltr">{{ destination.table.schema }}.{{ destination.table.name }}</code>
        </p>
        <div class="mt-1 flex flex-wrap items-center gap-1.5">
          <DataStatusBadge :status="destination.status" :label="t(`destinations.status.${destination.status}`)" />
          <UBadge :label="destination.table.created ? t('destinations.table.created') : t('destinations.table.yours')" color="neutral" variant="outline" size="sm" class="rounded-md" />
          <UBadge :label="destination.table.created ? t('destinations.options.write.standard') : t(`destinations.options.write.${destination.settings.write_mode}`)" color="neutral" variant="soft" size="sm" class="rounded-md" />
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <UDropdownMenu :items="menu" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
        <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="emit('close')" />
      </div>
    </div>

    <div v-if="can('data.storage')" class="flex flex-wrap items-center gap-2">
      <UButton :label="t('destinations.actions.backfill')" icon="i-lucide-history" color="neutral" size="sm" :disabled="busy || running || !destination.not_sent" @click="emit('backfill')" />
      <UButton v-if="destination.failed" :label="t('destinations.actions.retryAll', { n: destination.failed }, destination.failed)" icon="i-lucide-rotate-cw" color="neutral" variant="outline" size="sm" :loading="busy" @click="emit('retry')" />
      <USwitch :model-value="destination.status !== 'paused'" :label="destination.status === 'paused' ? t('destinations.paused') : t('destinations.delivering')" :disabled="busy" class="ms-auto" @update:model-value="value => emit('pause', !value)" />
    </div>
  </div>
</template>

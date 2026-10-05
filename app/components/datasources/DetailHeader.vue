<!--
  Connection panel header (F12, detail panel model): large engine mark, name, address, badges
  (status, engine and version, access), ⋯ (edit, duplicate, copy link, delete) and close; then
  the one-click bar: Test now, Edit, and the Enabled switch.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { DataSourceDetail } from '#shared/types/datasources'

const props = defineProps<{ source: DataSourceDetail; busy: boolean; testing: boolean }>()
const emit = defineEmits<{ test: []; enabled: [value: boolean]; duplicate: []; delete: []; close: [] }>()
const { t } = useI18n()
const toast = useToast()
const { copy } = useClipboard({ legacy: true })

const menu = computed<DropdownMenuItem[][]>(() => [
  [
    { label: t('dataSources.actions.edit'), icon: 'i-lucide-pencil', to: `/data-sources/connections/${props.source.id}/edit` },
    { label: t('dataSources.actions.duplicate'), icon: 'i-lucide-copy', onSelect: () => emit('duplicate') },
    {
      label: t('dataSources.actions.copyLink'),
      icon: 'i-lucide-link',
      onSelect: () => {
        void copy(`${location.origin}/data-sources/connections/${props.source.id}`)
        toast.add({ title: t('dataSources.toast.linkCopied'), color: 'success', icon: 'i-lucide-check' })
      },
    },
  ],
  [
    props.source.forms_count
      ? { label: t('dataSources.actions.deleteInUse'), icon: 'i-lucide-trash-2', disabled: true }
      : { label: t('dataSources.actions.delete'), icon: 'i-lucide-trash-2', color: 'error' as const, onSelect: () => emit('delete') },
  ],
])
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <div class="flex items-start gap-3.5">
      <DatasourcesEngineLogo :engine="source.engine" size="lg" />
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <h2 class="truncate text-lg leading-tight font-semibold text-highlighted">{{ source.name }}</h2>
        <p class="truncate text-start font-mono text-xs text-muted" dir="ltr">{{ source.address }}{{ source.database ? ` / ${source.database}` : '' }}</p>
        <div class="mt-1 flex flex-wrap items-center gap-1.5">
          <DataStatusBadge :status="source.status" />
          <UBadge :label="`${engineName(source.engine)}${source.server_version ? ` ${source.server_version}` : ''}`" color="neutral" variant="outline" size="sm" class="rounded-md" />
          <UBadge :label="t(`dataSources.access.${source.access.mode}`)" :icon="source.access.mode === 'read_only' ? 'i-lucide-eye' : 'i-lucide-pencil-line'" color="neutral" variant="soft" size="sm" class="rounded-md" />
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <UDropdownMenu :items="menu" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
        <UButton icon="i-lucide-x" color="neutral" variant="soft" size="sm" square class="rounded-full" :aria-label="t('common.close')" @click="emit('close')" />
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <UButton :label="t('dataSources.actions.test')" icon="i-lucide-activity" color="neutral" size="sm" :loading="testing" :disabled="!source.enabled || busy" @click="emit('test')" />
      <UButton :label="t('dataSources.actions.edit')" icon="i-lucide-pencil" color="neutral" variant="outline" size="sm" :to="`/data-sources/connections/${source.id}/edit`" />
      <USwitch :model-value="source.enabled" :label="source.enabled ? t('dataSources.enabled') : t('dataSources.disabledLabel')" :disabled="busy || testing" class="ms-auto" @update:model-value="value => emit('enabled', !!value)" />
    </div>
  </div>
</template>

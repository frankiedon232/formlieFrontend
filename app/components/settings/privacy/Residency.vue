<!--
  Settings → Privacy → Where data is stored (F14, leftovers L7, owner 2026-10-10): the workspace's region and what
  stays there (responses, files, backups, response emails, logs), and the regions Formalie can offer. Another
  region is an Enterprise service the Formalie team sets up (a move, never a switch here): on Enterprise, pick
  one and the Enterprise form opens with it filled in; on other plans, the plan that brings it and Contact us.
-->
<script setup lang="ts">
import type { DataRegion, DataRegionInfo } from '#shared/utils/platform/regions'

const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()
const { can } = useCan()
const { enquire } = useSupport()

// Flag per region (written out so the icon bundle has them)
const ICON: Record<DataRegion, string> = {
  default: 'i-lucide-globe',
  eu: 'i-circle-flags-eu',
  uk: 'i-circle-flags-gb',
  us: 'i-circle-flags-us',
  ca: 'i-circle-flags-ca',
  au: 'i-circle-flags-au',
  in: 'i-circle-flags-in',
  sg: 'i-circle-flags-sg',
  br: 'i-circle-flags-br',
}
const KEPT = ['responses', 'files', 'backups', 'emails', 'logs'] as const

const info = ref<DataRegionInfo | null>(null)
const failed = ref(false)
async function load() {
  failed.value = false
  try {
    info.value = (await api.get<DataRegionInfo>('/settings/data-region', undefined, { background: true })).data
  } catch (error) {
    failed.value = true
    handle(error, { silent: true })
  }
}
onMounted(load)

const others = computed(() => (info.value?.regions ?? []).filter(region => region !== info.value?.region && region !== 'default'))
const wanted = ref<DataRegion | undefined>()
const items = computed(() => others.value.map(value => ({ value, label: t(`settings.privacy.region.${value}`), icon: ICON[value] })))
const ask = () => enquire({ needs: 'residency', residency: wanted.value ? t(`settings.privacy.region.${wanted.value}`) : undefined })
</script>

<template>
  <AppEmpty v-if="failed && !info" size="xs" icon="i-lucide-cloud-off" :title="t('settings.privacy.regionFailed')" :actions="[{ label: t('common.retry'), icon: 'i-lucide-refresh-cw', color: 'neutral', variant: 'outline', onClick: load }]" />
  <div v-else-if="!info" class="flex flex-col gap-2"><USkeleton class="h-16 w-full" /><USkeleton class="h-8 w-2/3" /></div>
  <div v-else class="flex flex-col gap-4">
    <div class="flex items-start gap-3 rounded-lg border border-default p-3">
      <UIcon :name="ICON[info.region]" class="mt-0.5 size-6 shrink-0" />
      <div class="flex min-w-0 flex-col gap-1">
        <span class="text-sm font-medium text-highlighted">{{ t(`settings.privacy.region.${info.region}`) }}</span>
        <span class="text-xs text-muted">{{ t('settings.privacy.regionKept') }}</span>
        <div class="flex flex-wrap gap-1.5 pt-1">
          <UBadge v-for="item in KEPT" :key="item" :label="t(`settings.privacy.kept.${item}`)" color="neutral" variant="outline" size="sm" />
        </div>
      </div>
    </div>

    <div class="flex flex-col gap-2">
      <span class="text-xs font-medium text-muted">{{ t('settings.privacy.regionsOffered') }}</span>
      <div class="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1 [scrollbar-width:none]">
        <span v-for="region in others" :key="region" class="flex shrink-0 items-center gap-1.5 rounded-full border border-default px-2.5 py-1 text-xs text-default">
          <UIcon :name="ICON[region]" class="size-3.5" />{{ t(`settings.privacy.region.${region}`) }}
        </span>
      </div>
    </div>

    <div v-if="info.residency" class="flex flex-col gap-2 sm:flex-row sm:items-end">
      <UFormField :label="t('settings.privacy.regionWanted')" class="sm:w-72">
        <USelectMenu v-model="wanted" :items="items" value-key="value" :placeholder="t('settings.privacy.regionPick')" class="w-full" />
      </UFormField>
      <UButton v-if="can('settings.manage')" :label="t('settings.privacy.regionAsk')" icon="i-lucide-send" color="neutral" :disabled="!wanted" @click="ask" />
    </div>
    <template v-else>
      <BillingLocked feature="data_residency" />
      <UButton :label="t('billing.contactUs')" icon="i-lucide-messages-square" color="neutral" variant="outline" class="self-start" @click="ask" />
    </template>
    <p class="flex items-start gap-1.5 text-xs text-muted"><UIcon name="i-lucide-info" class="mt-0.5 size-3.5 shrink-0" />{{ t('settings.privacy.regionMove') }}</p>
  </div>
</template>

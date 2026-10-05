<!--
  Data sources overview (own rail area, F12). What each section does, with links (Connections is
  live since F12 M1; the rest follow), and the supported databases. The full plan is in PROGRESS.md → F12.
-->
<script setup lang="ts">
import { SUPPORTED_DATABASES } from '#shared/utils/integrations/databases'

definePageMeta({ breadcrumb: 'nav.dataSources' })
const { t } = useI18n()
useHead({ title: () => t('nav.dataSources') })

const sections = [
  { key: 'connections', nav: 'dataConnections', icon: 'i-lucide-database', to: '/data-sources/connections', live: true },
  { key: 'explorer', nav: 'dataExplorer', icon: 'i-lucide-table-2', to: '/data-sources/explorer' },
  { key: 'query', nav: 'dataQuery', icon: 'i-lucide-square-terminal', to: '/data-sources/query' },
  { key: 'savedQueries', nav: 'dataSavedQueries', icon: 'i-lucide-bookmark', to: '/data-sources/saved-queries' },
  { key: 'destinations', nav: 'destinations', icon: 'i-lucide-send', to: '/data-sources/destinations' },
  { key: 'transfers', nav: 'dataTransfers', icon: 'i-lucide-arrow-left-right', to: '/data-sources/transfers' },
  { key: 'activity', nav: 'dataActivity', icon: 'i-lucide-activity', to: '/data-sources/activity' },
]
</script>

<template>
  <AppPanel id="data-sources" :title="t('nav.dataSources')" :subtitle="t('dataSources.subtitle')">
    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <UPageCard
        v-for="section in sections"
        :key="section.key"
        :to="section.to"
        :icon="section.icon"
        :title="t(`nav.${section.nav}`)"
        :description="t(`dataSources.section.${section.key}`)"
        variant="outline"
        :ui="{ leadingIcon: 'size-5 text-default' }"
      >
        <template v-if="!section.live" #footer>
          <UBadge :label="t('placeholder.title')" color="neutral" variant="soft" size="sm" />
        </template>
      </UPageCard>
    </div>

    <UCard variant="outline" class="shrink-0">
      <div class="flex flex-col gap-3">
        <div>
          <p class="text-sm font-medium text-highlighted">{{ t('dataSources.engines') }}</p>
          <p class="text-sm text-muted">{{ t('dataSources.enginesHint') }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <UBadge v-for="db in SUPPORTED_DATABASES" :key="db.key" :label="db.name" icon="i-lucide-database" color="neutral" variant="outline" size="lg" />
          <UBadge :label="t('dataSources.builtIn')" icon="i-lucide-shield-check" color="neutral" variant="soft" size="lg" />
        </div>
      </div>
    </UCard>
  </AppPanel>
</template>

<!--
  Settings → Teams and locations (F14 M2): three optional lists on one page, switched at the start of
  the list's toolbar (`?list=teams | locations | cost_centres`, remembered in the address).
-->
<script setup lang="ts">
import type { OrgKind } from '#shared/types/org'

definePageMeta({ breadcrumb: 'settings.nav.places' })
const { t } = useI18n()
const route = useRoute()
const router = useRouter()
useHead({ title: () => t('settings.nav.places') })
const LISTS = ['teams', 'locations', 'cost_centres'] as const
const kind = computed<OrgKind>({
  get: () => (LISTS as readonly string[]).includes(String(route.query.list)) ? (route.query.list as OrgKind) : 'teams',
  set: value => void router.replace({ query: { list: value === 'teams' ? undefined : value } }),
})
const items = computed(() => LISTS.map(value => ({ value, label: t(`settings.org.kind.${value}.many`), icon: SETTINGS_ORG_ICONS[value] })))
</script>

<template>
  <SettingsOrgList :kind="kind">
    <template #toolbar-start>
      <UTabs v-model="kind" :items="items" :content="false" color="neutral" size="sm" :ui="SEGMENTED_UI" :aria-label="t('settings.nav.places')" />
    </template>
  </SettingsOrgList>
</template>

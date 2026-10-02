<!--
  Version history (FRONTEND-SPEC §6, PROGRESS F7): the current draft on top, then every published
  version as a timeline (design "Work Timeline" style) with View / Compare / Restore; the compare
  card shows what the draft changes against the chosen version.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'versions.crumb' })

const { t } = useI18n()
const route = useRoute()
const session = useBuilderSession(String(route.params.id))
const { form } = session
useHead({ title: () => (form.value ? `${form.value.name} · ${t('versions.crumb')}` : t('versions.crumb')) })
</script>

<template>
  <FormsBuilderFrame :session="session" mode="versions">
    <template #loading>
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]" :aria-label="t('common.loading')">
        <div class="flex flex-col gap-3">
          <USkeleton v-for="i in 4" :key="i" class="h-20 w-full" />
        </div>
        <USkeleton class="h-72 w-full" />
      </div>
    </template>

    <FormsVersionsHistory :session="session" />
  </FormsBuilderFrame>
</template>

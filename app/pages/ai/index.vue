<!--
  AI assistant overview (own rail area, F19). Placeholder: what the assistant will help with,
  and the promise that people stay in control. The full plan is in PROGRESS.md → F19.
-->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.ai' })
const { t } = useI18n()
useHead({ title: () => t('nav.ai') })

const sections = [
  { key: 'createForm', nav: 'aiCreateForm', icon: 'i-lucide-file-plus-2', to: '/ai/create-form' },
  { key: 'templates', nav: 'aiTemplates', icon: 'i-lucide-layout-template', to: '/ai/templates' },
  { key: 'analysis', nav: 'aiAnalysis', icon: 'i-lucide-chart-scatter', to: '/ai/analysis' },
  { key: 'insights', nav: 'aiInsights', icon: 'i-lucide-lightbulb', to: '/ai/insights' },
  { key: 'translate', nav: 'aiTranslate', icon: 'i-lucide-languages', to: '/ai/translate' },
  { key: 'history', nav: 'aiHistory', icon: 'i-lucide-history', to: '/ai/history' },
  { key: 'settings', nav: 'aiSettings', icon: 'i-lucide-sliders-horizontal', to: '/ai/settings' },
]
const promises = ['review', 'private', 'audit'] as const
</script>

<template>
  <AppPanel id="ai" :title="t('nav.ai')" :subtitle="t('ai.subtitle')">
    <UCard variant="outline" class="shrink-0">
      <div class="flex flex-col gap-3">
        <p class="text-sm font-medium text-highlighted">{{ t('ai.promise.title') }}</p>
        <ul class="grid gap-2 sm:grid-cols-3">
          <li v-for="item in promises" :key="item" class="flex items-start gap-2 text-sm text-muted">
            <UIcon name="i-lucide-check" class="mt-0.5 size-4 shrink-0 text-default" />
            {{ t(`ai.promise.${item}`) }}
          </li>
        </ul>
      </div>
    </UCard>

    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <UPageCard
        v-for="section in sections"
        :key="section.key"
        :to="section.to"
        :icon="section.icon"
        :title="t(`nav.${section.nav}`)"
        :description="t(`ai.section.${section.key}`)"
        variant="outline"
        :ui="{ leadingIcon: 'size-5 text-default' }"
      >
        <template #footer>
          <UBadge :label="t('placeholder.title')" color="neutral" variant="soft" size="sm" />
        </template>
      </UPageCard>
    </div>
  </AppPanel>
</template>

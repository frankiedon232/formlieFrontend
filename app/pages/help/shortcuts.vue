<!-- Help & support → Keyboard shortcuts (F25 M2): every shortcut, general, places you can open, and the ones that work on particular pages. -->
<script setup lang="ts">
definePageMeta({ breadcrumb: 'help.shortcuts.title' })
const { t } = useI18n()
useHead({ title: () => t('help.shortcuts.title') })
const { general, navigation, pages } = useShortcutList()
const sections = computed(() => [general.value, navigation.value, ...pages.value].filter(section => section.items.length))
</script>

<template>
  <AppPanel id="help-shortcuts" :title="t('help.shortcuts.title')" :subtitle="t('shortcuts.description')" subtitle-icon="i-lucide-keyboard">
    <template #actions>
      <UButton :label="t('help.back')" icon="i-lucide-circle-help" color="neutral" variant="outline" to="/help" />
    </template>

    <div class="grid items-start gap-4 md:grid-cols-2 xl:grid-cols-3">
      <UCard v-for="section in sections" :key="section.key" variant="outline" :ui="{ body: 'flex flex-col gap-2 p-4' }">
        <h2 class="text-sm font-semibold text-highlighted">{{ section.title }}</h2>
        <ul class="flex flex-col divide-y divide-default">
          <li v-for="item in section.items" :key="item.label" class="flex items-center justify-between gap-3 py-2 text-sm">
            <span class="text-default">{{ item.label }}</span>
            <span class="flex shrink-0 items-center gap-1">
              <template v-for="(key, index) in item.keys" :key="key">
                <span v-if="index && item.chain" class="text-xs text-muted">{{ t('shortcuts.then') }}</span>
                <UKbd :value="key" />
              </template>
            </span>
          </li>
        </ul>
      </UCard>
    </div>
    <p class="text-xs text-muted">{{ t('help.shortcuts.mac') }}</p>
  </AppPanel>
</template>

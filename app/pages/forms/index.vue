<!-- Placeholder until F5 (forms list). -->
<script setup lang="ts">
const { t } = useI18n()

useHead({ title: () => t('forms.title') })
</script>

<template>
  <UDashboardPanel id="forms">
    <template #header>
      <UDashboardNavbar :title="t('forms.title')">
        <template #right>
          <AppLocaleSwitch />
          <UColorModeButton />
        </template>
      </UDashboardNavbar>
    </template>

    <template #body>
      <UEmpty
        icon="i-lucide-file-text"
        :title="t('placeholder.title')"
        :description="t('forms.description')"
        class="my-auto"
      />
    </template>
  </UDashboardPanel>
</template>

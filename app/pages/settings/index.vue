<script setup lang="ts">
definePageMeta({ breadcrumb: 'nav.settings' })
const { t } = useI18n()
const session = useSession()
const isAdmin = computed(() => session.user.value?.role !== 'member')
useHead({ title: () => t('nav.settings') })
</script>

<template>
  <AppPanel id="settings" :title="t('nav.settings')">
    <div class="flex flex-col gap-6">
      <UPageCard
        v-if="isAdmin"
        :title="t('onboarding.settingsCard.title')"
        :description="t('onboarding.settingsCard.desc')"
        icon="i-lucide-list-checks"
        to="/onboarding"
        variant="outline"
        orientation="horizontal"
      >
        <div class="flex justify-end">
          <span class="inline-flex items-center gap-1 text-sm font-medium text-highlighted">
            {{ t('onboarding.settingsCard.open') }}
            <UIcon name="i-lucide-arrow-right" class="size-4 rtl:rotate-180" />
          </span>
        </div>
      </UPageCard>
      <AppComingSoon icon="i-lucide-settings" title-key="nav.settings" />
    </div>
  </AppPanel>
</template>

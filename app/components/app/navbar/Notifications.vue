<!-- Notifications slide-over. Real feed arrives with the backend; empty state until then. -->
<script setup lang="ts">
const { t } = useI18n()
const { notificationsOpen } = useAppUi()
const { endSide } = useAppLocale()
</script>

<template>
  <USlideover v-model:open="notificationsOpen" :title="t('navbar.notifications')" :side="endSide">
    <template #body>
      <UEmpty
        icon="i-lucide-bell"
        :title="t('navbar.noNotifications')"
        :description="t('navbar.noNotificationsDesc')"
        variant="naked"
        class="h-full"
      />
    </template>
  </USlideover>
</template>

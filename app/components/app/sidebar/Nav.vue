<script setup lang="ts">
defineProps<{ collapsed?: boolean }>()
const { t } = useI18n()
const { mainItems } = useNavigation()
</script>

<template>
  <nav :aria-label="t('nav.main')">
    <p v-if="!collapsed" class="mb-1 px-2.5 text-xs font-medium text-dimmed uppercase">
      {{ t('nav.main') }}
    </p>
    <UNavigationMenu :collapsed="collapsed" :items="mainItems" orientation="vertical" tooltip popover />
  </nav>
</template>

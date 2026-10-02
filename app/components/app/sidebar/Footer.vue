<script setup lang="ts">
defineProps<{ collapsed?: boolean }>()
const { t } = useI18n()
const { systemItems } = useNavigation()
const { shortcutsOpen } = useAppUi()

const helpItems = computed(() => [
  {
    label: t('shortcuts.title'),
    icon: 'i-lucide-keyboard',
    tooltip: { text: t('shortcuts.title'), kbds: ['?'] },
    onSelect: () => {
      shortcutsOpen.value = true
    },
  },
])
</script>

<template>
  <div class="flex w-full flex-col gap-2">
    <UNavigationMenu :collapsed="collapsed" :items="systemItems" orientation="vertical" tooltip />
    <UNavigationMenu :collapsed="collapsed" :items="helpItems" orientation="vertical" tooltip />
    <USeparator />
    <AppUserMenu :collapsed="collapsed" />
  </div>
</template>

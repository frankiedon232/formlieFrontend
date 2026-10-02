<!-- Workspace logo + name. F3 swaps in the tenant's logo, name and organisation switcher. -->
<script setup lang="ts">
defineProps<{ collapsed?: boolean }>()
const { t } = useI18n()
</script>

<template>
  <NuxtLink
    to="/forms"
    class="flex min-w-0 items-center gap-2 rounded-md font-semibold text-highlighted focus-visible:outline-2 focus-visible:outline-primary"
    :class="collapsed ? 'justify-center' : 'px-1.5'"
    :aria-label="t('app.name')"
  >
    <UIcon name="i-lucide-file-check-2" class="size-6 shrink-0 text-primary" />
    <span v-if="!collapsed" class="truncate">{{ t('app.name') }}</span>
  </NuxtLink>
</template>

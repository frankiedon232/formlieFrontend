<!--
  The menu column handed to a page (useSidebarTakeover): a header with the back arrow (to the
  menu), the page's title and «; the page teleports its content into the body below.
-->
<script setup lang="ts">
const emit = defineEmits<{ collapse: [] }>()
const { t } = useI18n()
const { owner, dismissed } = useSidebarTakeover()
</script>

<template>
  <div class="flex min-w-0 flex-1 flex-col">
    <div class="flex h-(--ui-header-height) shrink-0 items-center gap-2 border-b border-default px-3">
      <UTooltip :text="t('nav.backToMenu')">
        <UButton
          icon="i-lucide-arrow-left"
          color="neutral"
          variant="outline"
          size="xs"
          square
          :aria-label="t('nav.backToMenu')"
          class="rtl:-scale-x-100"
          @click="dismissed = true"
        />
      </UTooltip>
      <span class="min-w-0 flex-1 truncate text-sm font-semibold text-highlighted">{{ owner?.title }}</span>
      <UTooltip :text="t('nav.collapse')" :kbds="['[']">
        <UButton
          icon="i-lucide-chevrons-left"
          color="neutral"
          variant="outline"
          size="xs"
          square
          :aria-label="t('nav.collapse')"
          class="rtl:rotate-180"
          @click="emit('collapse')"
        />
      </UTooltip>
    </div>
    <div :id="SIDEBAR_TAKEOVER_ID" class="flex min-h-0 flex-1 flex-col" />
  </div>
</template>

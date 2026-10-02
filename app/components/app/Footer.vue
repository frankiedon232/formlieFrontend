<!--
  Slim footer (owner, 2026-10-02): © · version on the start side; help + shortcuts on the end side.
  Phones: one line (© · version); help lives in the menu drawer there. Privacy / Terms links join once the product website URLs exist.
-->
<script setup lang="ts">
// `minimal`: auth/public pages (no shortcuts dialog mounted there).
defineProps<{ minimal?: boolean }>()
const { t } = useI18n()
const config = useRuntimeConfig()
const { shortcutsOpen } = useAppUi()
const year = new Date().getFullYear()
</script>

<template>
  <footer
    class="flex shrink-0 items-center justify-center gap-2 border-t border-default px-4 py-2.5 text-xs text-muted sm:justify-between sm:px-6"
  >
    <p class="flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
      <span>© {{ year }} {{ t('app.name') }}. {{ t('footer.rights') }}</span>
      <span aria-hidden="true">·</span>
      <span>{{ t('footer.version', { version: config.public.appVersion }) }}</span>
    </p>
    <nav :aria-label="t('footer.label')" class="hidden flex-wrap items-center justify-center gap-1 sm:flex">
      <UButton
        :label="t('nav.help')"
        icon="i-lucide-circle-help"
        to="/help"
        color="neutral"
        variant="ghost"
        size="xs"
      />
      <UButton
        v-if="!minimal"
        :label="t('shortcuts.title')"
        icon="i-lucide-keyboard"
        color="neutral"
        variant="ghost"
        size="xs"
        @click="shortcutsOpen = true"
      />
    </nav>
  </footer>
</template>

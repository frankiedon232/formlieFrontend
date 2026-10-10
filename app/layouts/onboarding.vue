<!--
  Focused full-screen flow for the workspace set-up wizard: brand · language · theme · "Finish later",
  page content, slim footer. Same monochrome language as sign-in and the portal.
-->
<script setup lang="ts">
const { t } = useI18n()
const session = useSession()
</script>

<template>
  <div class="flex min-h-dvh flex-col bg-default">
    <header
      class="sticky top-0 z-10 flex items-center justify-between gap-2 border-b border-default bg-default/90 px-4 py-3 backdrop-blur sm:px-8"
    >
      <div class="flex min-w-0 items-center gap-2.5 font-semibold text-highlighted">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-lg bg-inverted text-inverted">
          <UIcon name="i-formalie-mark" class="size-4" />
        </span>
        <span class="hidden truncate tracking-tight sm:inline">{{
          session.tenant.value?.name ?? t('app.name')
        }}</span>
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <AppLocaleSwitch />
        <UColorModeButton color="neutral" variant="ghost" />
        <UButton
          :label="t('onboarding.later')"
          color="neutral"
          variant="outline"
          size="sm"
          to="/forms"
          class="ms-1"
        />
      </div>
    </header>

    <main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-8 sm:py-10">
      <slot />
    </main>

    <AppFooter minimal />
  </div>
</template>

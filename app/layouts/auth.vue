<!-- Login, OTP, signup, onboarding: centred card with branding, theme and language switches. -->
<script setup lang="ts">
const { t } = useI18n()
</script>

<template>
  <div class="flex min-h-dvh flex-col bg-muted">
    <header class="flex items-center justify-between gap-2 px-4 py-3 sm:px-6">
      <NuxtLink to="/" class="flex items-center gap-2 font-semibold text-highlighted">
        <UIcon name="i-lucide-file-check-2" class="size-6 text-primary" />
        <span>{{ t('app.name') }}</span>
      </NuxtLink>
      <div class="flex items-center gap-1">
        <AppLocaleSwitch />
        <UColorModeButton />
      </div>
    </header>
    <main class="flex flex-1 items-start justify-center px-4 py-6 sm:items-center sm:py-12">
      <div class="w-full max-w-md">
        <slot />
      </div>
    </main>
  </div>
</template>

<!--
  Sign-in / sign-up / OTP / recovery. lg+: inset dark showcase (AuthShowcase) | form column.
  Phones: brand bar + form. Language + theme always top-right; slim footer at the bottom.
  Monochrome, Manrope, clean dark text, same language as the portal (docs/design).
-->
<script setup lang="ts">
const { t } = useI18n()
const tenant = useTenant()
const brand = computed(() =>
  tenant.profile.value?.mode === 'tenant' ? tenant.profile.value.name : t('app.name'),
)
// The workspace's own branding (Settings → Branding, F14)
const own = computed(() => (tenant.profile.value?.mode === 'tenant' ? tenant.profile.value : null))
</script>

<template>
  <div class="flex min-h-dvh bg-default lg:p-3">
    <aside class="hidden w-[52%] max-w-[760px] shrink-0 lg:block">
      <AuthShowcase :workspace="!!own" :brand="brand" :logo="own?.logo_dark_url ?? own?.logo_url" :message="own?.signin_message" :color="own?.colors.primary" />
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center justify-between gap-2 px-5 py-4 sm:px-8">
        <NuxtLink
          to="/auth/login"
          class="flex items-center gap-2.5 font-semibold text-highlighted lg:invisible"
        >
          <span v-if="own?.logo_url" class="flex size-8 items-center justify-center overflow-hidden rounded-lg">
            <img :src="own.logo_url" alt="" class="max-h-full max-w-full object-contain" :class="own.logo_dark_url ? 'dark:hidden' : ''">
            <img v-if="own.logo_dark_url" :src="own.logo_dark_url" alt="" class="hidden max-h-full max-w-full object-contain dark:block">
          </span>
          <span v-else class="flex size-8 items-center justify-center rounded-lg bg-inverted text-inverted">
            <UIcon name="i-formalie-mark" class="size-4" />
          </span>
          <span class="truncate tracking-tight">{{ brand }}</span>
        </NuxtLink>
        <div class="flex items-center gap-1">
          <AppLocaleSwitch />
          <UColorModeButton color="neutral" variant="ghost" />
        </div>
      </header>

      <main class="flex flex-1 items-start justify-center px-5 pt-6 pb-10 sm:items-center sm:px-8 sm:py-10">
        <div class="w-full max-w-[400px] motion-safe:animate-rise">
          <slot />
          <!-- Whatever a workspace brands, Formalie stays visible (owner, 2026-10-07) -->
          <div v-if="own" class="mt-8 flex justify-center"><AppPoweredBy /></div>
        </div>
      </main>

      <AppFooter minimal />
    </div>
  </div>
</template>

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
</script>

<template>
  <div class="flex min-h-dvh bg-default lg:p-3">
    <aside class="hidden w-[52%] max-w-[760px] shrink-0 lg:block">
      <AuthShowcase :brand="brand" />
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center justify-between gap-2 px-5 py-4 sm:px-8">
        <NuxtLink
          to="/auth/login"
          class="flex items-center gap-2.5 font-semibold text-highlighted lg:invisible"
        >
          <span class="flex size-8 items-center justify-center rounded-lg bg-inverted text-inverted">
            <UIcon name="i-lucide-file-check-2" class="size-4" />
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
        </div>
      </main>

      <AppFooter minimal />
    </div>
  </div>
</template>

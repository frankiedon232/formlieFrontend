<!--
  Sign-in / sign-up / OTP / recovery. Same design language as the portal (docs/design: monochrome,
  Manrope, clean dark text): lg+ split — black brand panel (workspace name, value points) | form;
  phones — top bar (logo, language, theme) + form. Footer on both.
-->
<script setup lang="ts">
const { t } = useI18n()
const tenant = useTenant()
const brand = computed(() =>
  tenant.profile.value?.mode === 'tenant' ? tenant.profile.value.name : t('app.name'),
)
const initial = computed(() => brand.value.slice(0, 1).toUpperCase())

const points = computed(() => [
  { icon: 'i-lucide-mouse-pointer-click', text: t('authLayout.point1') },
  { icon: 'i-lucide-shield-check', text: t('authLayout.point2') },
  { icon: 'i-lucide-languages', text: t('authLayout.point3') },
])
</script>

<template>
  <div class="flex min-h-dvh bg-default">
    <aside
      class="relative hidden w-[44%] max-w-xl flex-col justify-between bg-inverted p-10 text-inverted lg:flex"
    >
      <div class="flex items-center gap-3">
        <span
          class="flex size-9 items-center justify-center rounded-lg bg-default text-lg font-semibold text-highlighted"
        >
          {{ initial }}
        </span>
        <span class="text-lg font-semibold">{{ brand }}</span>
      </div>

      <div class="space-y-8">
        <h2 class="text-3xl leading-tight font-semibold tracking-tight">{{ t('authLayout.headline') }}</h2>
        <ul class="space-y-4">
          <li v-for="point in points" :key="point.icon" class="flex items-start gap-3 text-sm opacity-90">
            <UIcon :name="point.icon" class="mt-0.5 size-5 shrink-0" />
            <span>{{ point.text }}</span>
          </li>
        </ul>
      </div>

      <p class="text-xs opacity-70">{{ t('authLayout.poweredBy', { app: t('app.name') }) }}</p>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center justify-between gap-2 px-4 py-3 sm:px-6">
        <NuxtLink
          to="/auth/login"
          class="flex items-center gap-2 font-semibold text-highlighted lg:invisible"
        >
          <span class="flex size-7 items-center justify-center rounded-md bg-inverted text-sm text-inverted">
            {{ initial }}
          </span>
          <span class="truncate">{{ brand }}</span>
        </NuxtLink>
        <div class="flex items-center gap-1">
          <AppLocaleSwitch />
          <UColorModeButton color="neutral" variant="ghost" />
        </div>
      </header>

      <main class="flex flex-1 items-start justify-center px-4 py-6 sm:items-center sm:px-6 sm:py-10">
        <div class="w-full max-w-sm">
          <slot />
        </div>
      </main>

      <AppFooter minimal />
    </div>
  </div>
</template>

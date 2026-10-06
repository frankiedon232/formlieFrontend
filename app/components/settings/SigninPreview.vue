<!--
  A live miniature of the workspace sign-in page (F14 M1, Settings → Branding), drawn from the draft:
  on the left the picture with the welcome (or the dark showcase with the logo for dark backgrounds,
  lit in the brand colour); on the right the logo, "Sign in to …" and the form. Light or dark, like
  people will see it. Decorative: hidden from assistive tech.
-->
<script setup lang="ts">
const props = defineProps<{ name: string; logo: string | null; logoDark: string | null; image: string | null; message: string | null; color: string | null; favicon: string | null }>()
const { t } = useI18n()
const mode = ref<'light' | 'dark'>('light')
const modes = computed(() => [
  { value: 'light', icon: 'i-lucide-sun', label: t('settings.branding.light') },
  { value: 'dark', icon: 'i-lucide-moon', label: t('settings.branding.dark') },
])
const accent = computed(() => props.color ?? '#7C3AED')
const formLogo = computed(() => (mode.value === 'dark' ? (props.logoDark ?? props.logo) : props.logo))
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-2">
      <span class="text-[11px] font-medium tracking-wide text-muted uppercase">{{ t('settings.branding.previewTitle') }}</span>
      <UTabs v-model="mode" :items="modes" :content="false" color="neutral" size="xs" :ui="SEGMENTED_UI" :aria-label="t('settings.branding.previewTitle')" />
    </div>
    <div aria-hidden="true" class="overflow-hidden rounded-xl border border-default shadow-sm">
      <!-- browser bar with the tab icon -->
      <div class="flex items-center gap-2 border-b border-default bg-elevated/60 px-3 py-2">
        <span class="flex gap-1"><span class="size-2 rounded-full bg-neutral-300 dark:bg-neutral-700" /><span class="size-2 rounded-full bg-neutral-300 dark:bg-neutral-700" /><span class="size-2 rounded-full bg-neutral-300 dark:bg-neutral-700" /></span>
        <span class="flex min-w-0 items-center gap-1.5 rounded-md bg-default px-2 py-0.5 text-[10px] text-muted">
          <img v-if="favicon ?? logo" :src="(favicon ?? logo)!" alt="" class="size-3 rounded-sm object-contain">
          <UIcon v-else name="i-lucide-file-check-2" class="size-3" />
          <span class="truncate">{{ t('settings.branding.tabTitle', { name }) }}</span>
        </span>
      </div>
      <div class="grid aspect-[16/9] grid-cols-[1.1fr_1fr]" :class="mode === 'dark' ? 'bg-neutral-950 text-white' : 'bg-white text-neutral-900'">
        <!-- showcase -->
        <div class="relative m-1.5 flex flex-col justify-between overflow-hidden rounded-lg bg-neutral-950 p-3 text-white">
          <img v-if="image" :src="image" alt="" class="absolute inset-0 size-full object-cover">
          <div v-if="image" class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-black/10" />
          <div v-else class="pointer-events-none absolute -right-8 -bottom-10 size-32 rounded-full opacity-50 blur-2xl" :style="{ backgroundColor: accent }" />
          <div class="relative flex items-center gap-1.5">
            <span v-if="logoDark ?? logo" class="flex size-5 items-center justify-center overflow-hidden rounded bg-white/90 p-0.5"><img :src="(logoDark ?? logo)!" alt="" class="max-h-full max-w-full object-contain"></span>
            <span v-else class="flex size-5 items-center justify-center rounded bg-white text-neutral-950"><UIcon name="i-lucide-file-check-2" class="size-3" /></span>
            <span class="truncate text-[10px] font-semibold">{{ name }}</span>
          </div>
          <p class="relative line-clamp-3 text-[11px] leading-snug font-semibold">{{ message || t('authLayout.headline') }}</p>
        </div>
        <!-- sign-in form -->
        <div class="flex flex-col justify-center gap-2 px-4">
          <span v-if="formLogo" class="flex size-6 items-center justify-center overflow-hidden rounded-md"><img :src="formLogo" alt="" class="max-h-full max-w-full object-contain"></span>
          <span class="text-[11px] font-semibold">{{ t('settings.branding.signinTo', { name }) }}</span>
          <span class="h-4 rounded border" :class="mode === 'dark' ? 'border-white/15 bg-white/5' : 'border-neutral-200 bg-white'" />
          <span class="h-4 rounded border" :class="mode === 'dark' ? 'border-white/15 bg-white/5' : 'border-neutral-200 bg-white'" />
          <span class="h-4 rounded" :class="mode === 'dark' ? 'bg-white' : 'bg-neutral-900'" />
          <span class="h-0.5 w-8 rounded-full" :style="{ backgroundColor: accent }" />
        </div>
      </div>
    </div>
  </div>
</template>

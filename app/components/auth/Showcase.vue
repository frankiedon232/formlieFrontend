<!--
  Auth showcase (lg+): inset dark panel with depth (grid, glow), the headline, and data on the move (AuthFlow:
  form link, embed, API and QR code send points of light through the hub to your database, webhooks, dashboard
  and email; owner 2026-10-10), then the trust badges. Motion only for people who allow it. Decorative: hidden
  from assistive tech except the copy.
  A workspace's own branding (Settings → Branding, F14) takes over: its logo for dark backgrounds,
  its welcome as the headline, its brand colour in the glow. No organisation picture fills the panel (owner
  2026-10-10: the design stays; their logo at the top is enough).
-->
<script setup lang="ts">
// Explicit import: shared constant (a new shared/utils folder is only auto-imported after a dev restart).
import { SUPPORTED_DATABASES } from '#shared/utils/integrations/databases'

const props = defineProps<{ brand: string; logo?: string | null; message?: string | null; color?: string | null; workspace?: boolean }>()
const { t } = useI18n()
const databaseCount = SUPPORTED_DATABASES.length
const badges = computed(() => [
  { icon: 'i-lucide-lock-keyhole', label: t('authLayout.badgeEncrypted') },
  { icon: 'i-lucide-scale', label: t('authLayout.badgeCompliance') },
  { icon: 'i-lucide-database', label: t('authLayout.badgeDatabase', { count: databaseCount }) },
  { icon: 'i-lucide-users-round', label: t('authLayout.badgeAccess') },
  { icon: 'i-lucide-globe', label: t('authLayout.badgeLanguages') },
])
</script>

<template>
  <div
    class="relative flex h-full flex-col overflow-hidden rounded-3xl bg-neutral-950 p-10 text-white ring-1 ring-white/10 xl:p-12"
  >
    <!-- depth: faint grid fading out at the edges + two soft glows -->
    <div
      aria-hidden="true"
      class="pointer-events-none absolute inset-0 [mask-image:radial-gradient(ellipse_at_center,black_35%,transparent_75%)] bg-[linear-gradient(to_right,rgb(255_255_255/0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgb(255_255_255/0.06)_1px,transparent_1px)] bg-[size:44px_44px]"
    />
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -top-48 -right-40 size-[560px] rounded-full bg-white/10 blur-3xl"
    />
    <div
      aria-hidden="true"
      class="pointer-events-none absolute -bottom-56 -left-40 size-[480px] rounded-full blur-3xl"
      :class="props.color ? 'opacity-30' : 'bg-violet-500/25'"
      :style="props.color ? { backgroundColor: props.color } : undefined"
    />

    <div class="relative flex items-center gap-3">
      <span v-if="props.logo" class="flex size-9 items-center justify-center overflow-hidden rounded-xl bg-white/95 p-1">
        <img :src="props.logo" alt="" class="max-h-full max-w-full object-contain">
      </span>
      <span v-else class="flex size-9 items-center justify-center rounded-xl bg-white text-neutral-950">
        <UIcon name="i-lucide-file-check-2" class="size-5" />
      </span>
      <span class="text-lg font-semibold tracking-tight">{{ props.brand }}</span>
      <AppPoweredBy v-if="workspace" tone="light" class="ms-auto" />
    </div>

    <div class="relative mt-10 max-w-lg">
      <h2 class="text-4xl leading-[1.08] font-semibold tracking-tight xl:text-[44px]">
        {{ props.message || t('authLayout.headline') }}
      </h2>
      <p class="mt-4 text-[15px] leading-relaxed text-white/60">{{ t('authLayout.subline') }}</p>
    </div>

    <!-- Data on the move: sources → the hub → destinations (owner 2026-10-10) -->
    <div class="relative mt-6 flex flex-1 items-center">
      <AuthFlow :color="props.color" />
    </div>

    <div class="relative mt-8 flex flex-wrap gap-2">
      <span
        v-for="badge in badges"
        :key="badge.icon"
        class="inline-flex items-center gap-1.5 rounded-full bg-white/5 px-3 py-1.5 text-xs text-white/80 ring-1 ring-white/10"
      >
        <UIcon :name="badge.icon" class="size-3.5" />
        {{ badge.label }}
      </span>
    </div>
  </div>
</template>

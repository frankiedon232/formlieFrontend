<!--
  Auth showcase (lg+): inset dark panel with depth (grid, glow) + a live-looking product preview
  composed from real Nuxt UI parts, telling the platform story (global, any organisation):
  build any form · collect data · sync to your own database · control access.
  Floats gently (motion-safe only). Decorative: hidden from assistive tech except the copy.
-->
<script setup lang="ts">
const props = defineProps<{ brand: string }>()
const { t } = useI18n()
const { number } = useFormat()

const bars = [38, 52, 44, 70, 58, 86, 74]
const badges = computed(() => [
  { icon: 'i-lucide-lock-keyhole', label: t('authLayout.badgeEncrypted') },
  { icon: 'i-lucide-scale', label: t('authLayout.badgeCompliance') },
  { icon: 'i-lucide-database', label: t('authLayout.badgeDatabase') },
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
      class="pointer-events-none absolute -bottom-56 -left-40 size-[480px] rounded-full bg-violet-500/25 blur-3xl"
    />

    <div class="relative flex items-center gap-3">
      <span class="flex size-9 items-center justify-center rounded-xl bg-white text-neutral-950">
        <UIcon name="i-lucide-file-check-2" class="size-5" />
      </span>
      <span class="text-lg font-semibold tracking-tight">{{ props.brand }}</span>
    </div>

    <div class="relative mt-12 max-w-lg">
      <h2 class="text-4xl leading-[1.08] font-semibold tracking-tight xl:text-[44px]">
        {{ t('authLayout.headline') }}
      </h2>
      <p class="mt-4 text-[15px] leading-relaxed text-white/60">{{ t('authLayout.subline') }}</p>
    </div>

    <!-- product preview: build · collect · connect · control -->
    <div aria-hidden="true" class="relative mt-10 min-h-[360px] flex-1">
      <UCard
        class="absolute top-0 left-0 w-[310px] -rotate-2 shadow-2xl shadow-black/40 motion-safe:animate-float"
        :ui="{ body: 'space-y-4 p-5 sm:p-5' }"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="flex size-7 items-center justify-center rounded-lg bg-inverted text-inverted">
              <UIcon name="i-lucide-clipboard-list" class="size-4" />
            </span>
            <span class="text-sm font-semibold text-highlighted">{{ t('authLayout.previewForm') }}</span>
          </div>
          <UBadge
            :label="t('status.published')"
            color="success"
            variant="subtle"
            size="sm"
            class="rounded-md"
          />
        </div>
        <div class="space-y-1.5">
          <p class="text-xs font-medium text-default">{{ t('authLayout.previewCompany') }}</p>
          <UInput
            model-value="Northwind Ltd."
            disabled
            class="w-full"
            :ui="{ base: 'disabled:opacity-100' }"
          />
        </div>
        <div class="space-y-1.5">
          <p class="text-xs font-medium text-default">{{ t('authLayout.previewConsent') }}</p>
          <div class="flex items-center gap-2 text-xs text-default">
            <UCheckbox :model-value="true" disabled :ui="{ base: 'disabled:opacity-100' }" />
            {{ t('authLayout.previewConsentText') }}
          </div>
        </div>
        <UButton :label="t('authLayout.previewSubmit')" color="neutral" block tabindex="-1" />
      </UCard>

      <UCard
        class="absolute top-12 right-0 w-[240px] rotate-3 shadow-2xl shadow-black/40 motion-safe:animate-float-delayed"
        :ui="{ body: 'p-5 sm:p-5' }"
      >
        <p class="text-xs text-muted">{{ t('authLayout.previewStat') }}</p>
        <div class="mt-1 flex items-end gap-2">
          <span class="text-3xl font-semibold tracking-tight text-highlighted">{{ number(12840) }}</span>
          <UBadge label="+12%" color="success" variant="subtle" size="sm" class="mb-1 rounded-md" />
        </div>
        <div class="mt-4 flex h-16 items-end gap-1.5">
          <span
            v-for="(height, index) in bars"
            :key="index"
            class="flex-1 rounded-sm"
            :class="index === bars.length - 2 ? 'bg-inverted' : 'bg-accented'"
            :style="{ height: `${height}%` }"
          />
        </div>
        <div class="mt-4 flex items-center gap-1.5 border-t border-default pt-3 text-xs text-muted">
          <UIcon name="i-lucide-users-round" class="size-3.5" />
          {{ t('authLayout.previewAccess') }}
        </div>
      </UCard>

      <UCard
        class="absolute bottom-2 left-20 w-[310px] shadow-2xl shadow-black/40 motion-safe:animate-float"
        :ui="{ body: 'flex items-center gap-3 p-4 sm:p-4' }"
      >
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-lg bg-elevated text-highlighted"
        >
          <UIcon name="i-lucide-database-zap" class="size-5" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-semibold text-highlighted">{{ t('authLayout.previewSync') }}</p>
          <p class="truncate text-xs text-muted">
            {{ t('authLayout.previewSyncMeta', { rows: number(12840) }) }}
          </p>
        </div>
        <UIcon name="i-lucide-circle-check" class="size-5 text-success" />
      </UCard>
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

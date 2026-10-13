<script setup lang="ts">
// Enterprise, drawn: your workspace connected to your region over an encrypted line, with the commitments ticking
// in one by one. SVG and CSS only; still for reduced motion; paused off screen.
const { t, tm, rt } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { still, paused } = useSectionMotion(root)

const checks = computed(() =>
  (tm('enterprisePage.visual.checks') as unknown[]).map(item => rt(item as string)),
)
const ICONS = ['i-lucide-key-round', 'i-lucide-activity', 'i-lucide-shield-check', 'i-lucide-receipt']
</script>

<template>
  <div
    ref="root"
    aria-hidden="true"
    class="relative isolate overflow-hidden rounded-3xl bg-neutral-950 p-6 text-white shadow-2xl shadow-black/20 ring-1 ring-white/10 sm:p-8"
    :class="{ 'motion-paused': paused }"
  >
    <div
      class="absolute inset-0 -z-10 opacity-50"
      style="
        background-image:
          linear-gradient(rgb(255 255 255 / 0.05) 1px, transparent 1px),
          linear-gradient(90deg, rgb(255 255 255 / 0.05) 1px, transparent 1px);
        background-size: 28px 28px;
      "
    />
    <div class="absolute -end-24 -bottom-24 -z-10 size-80 rounded-full bg-violet-600/30 blur-3xl" />

    <!-- Workspace ⇄ region -->
    <div class="relative flex items-center justify-between gap-3" dir="ltr">
      <div class="flex flex-col items-center gap-2">
        <img
          src="/brand/formalie-mark-inverse.svg"
          alt=""
          width="56"
          height="56"
          class="size-14 rounded-2xl shadow-[0_0_40px_rgb(255_255_255/0.2)]"
        />
        <span class="text-xs text-white/70">{{ t('enterprisePage.visual.workspace') }}</span>
      </div>

      <svg viewBox="0 0 200 20" class="h-5 flex-1 overflow-visible">
        <line x1="0" y1="10" x2="200" y2="10" stroke="white" stroke-opacity="0.15" stroke-width="1.5" />
        <line
          x1="0"
          y1="10"
          x2="200"
          y2="10"
          stroke="#a78bfa"
          stroke-opacity="0.7"
          stroke-width="1.5"
          stroke-dasharray="2 10"
          class="motion-safe:animate-dash"
        />
        <g v-if="!still">
          <circle r="4" cy="10" fill="#ffffff">
            <animate attributeName="cx" values="0;200" dur="2.4s" repeatCount="indefinite" />
          </circle>
          <circle r="4" cy="10" fill="#a78bfa">
            <animate attributeName="cx" values="200;0" dur="2.4s" begin="1.2s" repeatCount="indefinite" />
          </circle>
        </g>
        <g transform="translate(100 10)">
          <circle r="11" fill="#0a0a0a" stroke="white" stroke-opacity="0.3" />
        </g>
      </svg>

      <div class="flex flex-col items-center gap-2">
        <span
          class="relative flex size-14 items-center justify-center rounded-2xl bg-white/10 ring-1 ring-white/20"
        >
          <UIcon name="i-lucide-globe" class="size-6" />
          <span class="absolute -end-1 -top-1 flex size-3">
            <span
              class="absolute inline-flex size-full rounded-full bg-emerald-400 motion-safe:animate-ping-soft"
            />
            <span class="relative inline-flex size-3 rounded-full bg-emerald-400" />
          </span>
        </span>
        <span class="text-xs text-white/70">{{ t('enterprisePage.visual.region') }}</span>
      </div>
    </div>

    <!-- The commitments, arriving one by one -->
    <ul class="mt-8 space-y-2">
      <li
        v-for="(check, i) in checks"
        :key="check"
        class="flex items-center gap-3 rounded-xl bg-white/[0.05] px-3 py-2.5 ring-1 ring-white/10 motion-safe:animate-rise"
        :style="{ animationDelay: `${300 + i * 250}ms` }"
      >
        <span class="flex size-8 items-center justify-center rounded-lg bg-white text-neutral-950">
          <UIcon :name="ICONS[i]!" class="size-4" />
        </span>
        <span class="flex-1 text-sm font-medium">{{ check }}</span>
        <UIcon name="i-lucide-circle-check" class="size-5 text-emerald-300" />
      </li>
    </ul>
  </div>
</template>

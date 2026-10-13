<script setup lang="ts">
// "How it works": three numbered steps joined by a line that a point of light travels along.
defineProps<{ steps: { title: string; text: string }[] }>()
const { t } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { still, paused } = useSectionMotion(root)
</script>

<template>
  <UPageSection :title="t('common.howItWorks')">
    <div ref="root" class="relative" :class="{ 'motion-paused': paused }">
      <!-- The line between the steps (desktop), with a travelling point -->
      <svg
        aria-hidden="true"
        viewBox="0 0 600 10"
        preserveAspectRatio="none"
        class="absolute inset-x-[16%] top-6 hidden h-2.5 w-[68%] overflow-visible md:block rtl:-scale-x-100"
      >
        <line x1="0" y1="5" x2="600" y2="5" stroke="var(--ui-border-accented)" stroke-width="1.5" />
        <line
          x1="0"
          y1="5"
          x2="600"
          y2="5"
          stroke="#8b5cf6"
          stroke-opacity="0.6"
          stroke-width="1.5"
          stroke-dasharray="2 10"
          class="motion-safe:animate-dash"
        />
        <circle v-if="!still" r="4" cy="5" fill="#8b5cf6">
          <animate attributeName="cx" values="0;600" dur="4s" repeatCount="indefinite" />
          <animate
            attributeName="opacity"
            values="0;1;1;0"
            keyTimes="0;0.1;0.9;1"
            dur="4s"
            repeatCount="indefinite"
          />
        </circle>
      </svg>

      <ol class="relative grid gap-10 md:grid-cols-3">
        <li v-for="(step, i) in steps" :key="step.title" class="flex flex-col items-center text-center">
          <span
            class="relative flex size-12 items-center justify-center rounded-full bg-inverted text-base font-semibold text-inverted shadow-lg shadow-black/10 ring-8 ring-default"
          >
            {{ i + 1 }}
          </span>
          <span class="sr-only">{{ t('common.step', { n: i + 1 }) }}</span>
          <h3 class="mt-5 text-lg font-semibold text-highlighted">{{ step.title }}</h3>
          <p class="mt-1 max-w-xs text-sm text-muted">{{ step.text }}</p>
        </li>
      </ol>
    </div>
  </UPageSection>
</template>

<script setup lang="ts">
// The dashboard, animated: the numbers count up, the activity line draws itself across the period, and the
// tooltip pops on the latest day. Illustrative sample values.
const { t, locale } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { step, live } = useDemoLoop(root, 3, 1300, 3)

const POINTS = [62, 48, 40, 52, 66, 60, 58, 44, 36, 54, 70, 66, 68, 50, 34, 58, 74, 80]
const W = 360
const H = 120
const x = (i: number) => (i / (POINTS.length - 1)) * W
const y = (v: number) => H - (v / 100) * H
const line = POINTS.map((v, i) => `${i ? 'L' : 'M'} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ')
const area = `${line} L ${W} ${H} L 0 ${H} Z`
const last = { x: x(POINTS.length - 1), y: y(POINTS[POINTS.length - 1]!) }

const n = (value: number, digits = 0) =>
  new Intl.NumberFormat(locale.value, {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value)
const progress = computed(() => step.value / 3)
const kpis = computed(() => [
  { label: t('demo.responses'), value: n(Math.round(15249 * (0.6 + 0.4 * progress.value))), trend: '+17%' },
  { label: t('demo.completion'), value: `${n(71.4 * (0.8 + 0.2 * progress.value), 1)}%`, trend: '+4%' },
  { label: t('demo.apiCalls'), value: n(Math.round(4812 * (0.6 + 0.4 * progress.value))), trend: '+9%' },
])
</script>

<template>
  <div ref="root">
    <DemoWindow :title="t('home.tabs.dashboard.label')" icon="i-lucide-layout-dashboard">
      <div class="grid grid-cols-3 gap-2">
        <div v-for="kpi in kpis" :key="kpi.label" class="rounded-xl p-2.5 ring-1 ring-default">
          <p class="truncate text-[10px] text-muted">{{ kpi.label }}</p>
          <p class="mt-0.5 text-base font-semibold tracking-tight text-highlighted tabular-nums sm:text-lg">
            {{ kpi.value }}
          </p>
          <span
            class="mt-1 inline-flex rounded-full bg-emerald-500/10 px-1.5 text-[9px] font-medium text-emerald-700 dark:text-emerald-300"
            >{{ kpi.trend }}</span
          >
        </div>
      </div>

      <div class="mt-3 rounded-xl p-3 ring-1 ring-default">
        <div class="flex items-baseline justify-between gap-2">
          <p class="text-[11px] font-semibold text-highlighted">{{ t('demo.activity') }}</p>
          <span class="flex items-center gap-3 text-[9px] text-muted">
            <span class="flex items-center gap-1"
              ><span class="size-1.5 rounded-full bg-inverted" />{{ t('demo.started') }}</span
            >
            <span class="flex items-center gap-1"
              ><span class="size-1.5 rounded-full bg-emerald-500" />{{ t('demo.sent') }}</span
            >
          </span>
        </div>
        <div class="relative mt-2">
          <svg
            :viewBox="`0 0 ${W} ${H + 4}`"
            class="h-32 w-full overflow-visible"
            preserveAspectRatio="none"
            dir="ltr"
          >
            <path :d="area" class="fill-violet-500/10" />
            <path
              :key="live ? `line-${step === 0}` : 'line'"
              :d="line"
              fill="none"
              stroke="currentColor"
              class="text-highlighted"
              stroke-width="2"
              stroke-linejoin="round"
              vector-effect="non-scaling-stroke"
              pathLength="1"
              :stroke-dasharray="live ? 1 : undefined"
              :stroke-dashoffset="live ? 1 - progress : undefined"
              style="transition: stroke-dashoffset 1.2s ease-out"
            />
            <circle v-if="step >= 3" :cx="last.x" :cy="last.y" r="4" class="fill-emerald-500" />
          </svg>
          <div
            v-if="step >= 3"
            class="absolute end-0 top-0 rounded-xl bg-default px-3 py-2 shadow-xl ring-1 ring-default motion-safe:animate-pop"
          >
            <p class="text-sm font-semibold text-highlighted tabular-nums">{{ n(71.4, 1) }}%</p>
            <p class="text-[9px] text-muted">{{ t('demo.completion') }}</p>
          </div>
        </div>
      </div>
    </DemoWindow>
  </div>
</template>

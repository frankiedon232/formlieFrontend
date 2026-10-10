<!--
  Sign-in showcase: data on the move (owner 2026-10-10, after two concepts: a hub with labelled pills joined by
  curved lines that carry points of light, and response cards floating while they are collected). Sources on the
  left (form link, embed, API, QR code) send points of light through the hub (always Formalie, owner 2026-10-10:
  the workspace's logo is at the top of the panel; a lock: encrypted on the way) to destinations on the right (your database, webhooks, dashboard, email), which
  light up as one arrives. SVG and CSS only; nothing moves for people who ask for less motion. Decorative.
-->
<script setup lang="ts">
const props = defineProps<{ color?: string | null }>()
const { t } = useI18n()
const still = useMediaQuery('(prefers-reduced-motion: reduce)')

// One drawing space (600 × 400); the pills sit at the same points, in percent, so everything scales together
const W = 600
const H = 400
const HUB = { x: 300, y: 200 }
const SOURCES = [
  { key: 'link', icon: 'i-lucide-link', y: 64 },
  { key: 'embed', icon: 'i-lucide-code-xml', y: 154 },
  { key: 'api', icon: 'i-lucide-braces', y: 246 },
  { key: 'qr', icon: 'i-lucide-qr-code', y: 336 },
]
const TARGETS = [
  { key: 'database', icon: 'i-lucide-database', y: 64 },
  { key: 'webhook', icon: 'i-lucide-webhook', y: 154 },
  { key: 'dashboard', icon: 'i-lucide-chart-column', y: 246 },
  { key: 'email', icon: 'i-lucide-mail-check', y: 336 },
]
const SOURCE_X = 80
const TARGET_X = 520
/** Half a pill's width in the drawing (pills are 26% wide). */
const HALF = 78
/** Which destination each source's data goes to (crossed, so the picture isn't four parallel lanes). */
const ROUTES = [1, 0, 3, 2]
const CYCLE = 4 // seconds a point of light takes from source to destination
const STAGGER = CYCLE / ROUTES.length

const inbound = (y: number) => `M ${SOURCE_X + HALF} ${y} C ${SOURCE_X + 160} ${y}, ${HUB.x - 110} ${HUB.y}, ${HUB.x - 34} ${HUB.y}`
const outbound = (y: number) => `M ${HUB.x + 34} ${HUB.y} C ${HUB.x + 110} ${HUB.y}, ${TARGET_X - 160} ${y}, ${TARGET_X - HALF} ${y}`
/** The whole route of one point of light: source → hub → destination. */
const route = (from: number, to: number) => `${inbound(SOURCES[from]!.y)} L ${HUB.x + 34} ${HUB.y} ${outbound(TARGETS[to]!.y).replace(/^M [^C]+/, '')}`
const at = (x: number, y: number) => ({ left: `${(x / W) * 100}%`, top: `${(y / H) * 100}%` })
const light = computed(() => props.color || '#ffffff')

/** Faint response cards drifting up behind the hub (the "being collected" feeling). */
const CARDS = [
  { x: 214, y: 92, w: 70, delay: 0 },
  { x: 372, y: 110, w: 58, delay: 2.2 },
  { x: 232, y: 336, w: 62, delay: 1.1 },
  { x: 372, y: 330, w: 74, delay: 3.4 },
]
</script>

<template>
  <div aria-hidden="true" dir="ltr" class="relative mx-auto aspect-[3/2] w-full max-w-[640px] select-none">
    <!-- Drifting response cards -->
    <div
      v-for="(card, i) in CARDS"
      :key="`card-${i}`"
      class="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col gap-1 rounded-md bg-white/[0.04] p-1.5 ring-1 ring-white/10 motion-safe:animate-drift"
      :style="{ ...at(card.x, card.y), width: `${(card.w / W) * 100}%`, animationDelay: `${card.delay}s` }"
    >
      <span class="h-1 w-3/4 rounded-full bg-white/25" />
      <span class="h-1 w-1/2 rounded-full bg-white/15" />
      <span class="h-1 w-2/3 rounded-full bg-white/10" />
    </div>

    <svg :viewBox="`0 0 ${W} ${H}`" class="absolute inset-0 size-full overflow-visible">
      <defs>
        <filter id="flow-glow" x="-200%" y="-200%" width="500%" height="500%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
        <radialGradient id="flow-hub" cx="50%" cy="50%" r="50%">
          <stop offset="0%" :stop-color="light" stop-opacity="0.35" />
          <stop offset="100%" :stop-color="light" stop-opacity="0" />
        </radialGradient>
      </defs>

      <!-- The lines -->
      <path v-for="(source, i) in SOURCES" :key="`in-${i}`" :d="inbound(source.y)" fill="none" stroke="white" stroke-opacity="0.16" stroke-width="1.2" />
      <path v-for="(target, i) in TARGETS" :key="`out-${i}`" :d="outbound(target.y)" fill="none" stroke="white" stroke-opacity="0.16" stroke-width="1.2" />
      <path v-for="(source, i) in SOURCES" :key="`in-dash-${i}`" :d="inbound(source.y)" fill="none" stroke="white" stroke-opacity="0.35" stroke-width="1.2" stroke-dasharray="2 10" class="motion-safe:animate-dash" />
      <path v-for="(target, i) in TARGETS" :key="`out-dash-${i}`" :d="outbound(target.y)" fill="none" stroke="white" stroke-opacity="0.35" stroke-width="1.2" stroke-dasharray="2 10" class="motion-safe:animate-dash" />

      <!-- The hub's halo and its pulse as each point passes -->
      <circle :cx="HUB.x" :cy="HUB.y" r="92" fill="url(#flow-hub)" />
      <circle :cx="HUB.x" :cy="HUB.y" r="44" fill="none" stroke="white" stroke-opacity="0.18" />
      <circle v-if="!still" :cx="HUB.x" :cy="HUB.y" r="40" fill="none" :stroke="light" stroke-width="1.5">
        <animate attributeName="r" values="40;78" :dur="`${STAGGER}s`" repeatCount="indefinite" />
        <animate attributeName="stroke-opacity" values="0.55;0" :dur="`${STAGGER}s`" repeatCount="indefinite" />
      </circle>

      <!-- Points of light: one per route, one after another -->
      <template v-if="!still">
        <g v-for="(to, from) in ROUTES" :key="`dot-${from}`">
          <!-- Hidden until its turn: before it starts, a point would sit in the corner -->
          <circle r="7" :fill="light" opacity="0" filter="url(#flow-glow)">
            <set attributeName="opacity" to="0.5" :begin="`${from * STAGGER}s`" />
            <animateMotion :path="route(from, to)" :dur="`${CYCLE}s`" :begin="`${from * STAGGER}s`" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.45 0 0.55 1" />
          </circle>
          <circle r="3" fill="white" opacity="0">
            <set attributeName="opacity" to="1" :begin="`${from * STAGGER}s`" />
            <animateMotion :path="route(from, to)" :dur="`${CYCLE}s`" :begin="`${from * STAGGER}s`" repeatCount="indefinite" calcMode="spline" keyTimes="0;1" keySplines="0.45 0 0.55 1" />
          </circle>
          <!-- The destination lights up as it arrives -->
          <rect :x="TARGET_X - HALF" :y="TARGETS[to]!.y - 17" :width="HALF * 2" height="34" rx="17" fill="none" :stroke="light" stroke-width="1.5" opacity="0">
            <animate attributeName="opacity" values="0;0;0.9;0" keyTimes="0;0.86;0.93;1" :dur="`${CYCLE}s`" :begin="`${from * STAGGER}s`" repeatCount="indefinite" />
          </rect>
        </g>
      </template>
    </svg>

    <!-- The hub -->
    <div class="absolute flex aspect-square w-[13%] -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-2xl bg-white text-neutral-950 shadow-[0_0_40px_rgb(255_255_255/0.25)]" :style="at(HUB.x, HUB.y)">
      <UIcon name="i-formalie-mark" class="size-1/2" />
      <span class="absolute -end-2 -bottom-2 flex size-6 items-center justify-center rounded-full bg-neutral-950 text-white ring-2 ring-white"><UIcon name="i-lucide-lock-keyhole" class="size-3" /></span>
    </div>
    <span class="absolute -translate-x-1/2 text-[11px] whitespace-nowrap text-white/60" :style="at(HUB.x, HUB.y + 62)">{{ t('authLayout.flow.hub') }}</span>

    <!-- Sources and destinations -->
    <span
      v-for="item in SOURCES"
      :key="item.key"
      class="absolute flex w-[26%] -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-full bg-white/[0.06] py-1.5 ps-1.5 pe-3 text-xs text-white/85 ring-1 ring-white/15 backdrop-blur-sm"
      :style="at(SOURCE_X, item.y)"
    >
      <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-white/10"><UIcon :name="item.icon" class="size-3.5" /></span>
      <span class="truncate">{{ t(`authLayout.flow.${item.key}`) }}</span>
    </span>
    <span
      v-for="item in TARGETS"
      :key="item.key"
      class="absolute flex w-[26%] -translate-x-1/2 -translate-y-1/2 items-center gap-2 rounded-full bg-white/[0.06] py-1.5 ps-1.5 pe-3 text-xs text-white/85 ring-1 ring-white/15 backdrop-blur-sm"
      :style="at(TARGET_X, item.y)"
    >
      <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-white text-neutral-950"><UIcon :name="item.icon" class="size-3.5" /></span>
      <span class="truncate">{{ t(`authLayout.flow.${item.key}`) }}</span>
    </span>
  </div>
</template>

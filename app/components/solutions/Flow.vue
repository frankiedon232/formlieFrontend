<script setup lang="ts">
// A solution's data flow (drawn): its two templates send answers through the Formalie hub to where the data goes.
// SVG lines with travelling points; still for reduced motion; paused off screen.
const props = defineProps<{ templates: { icon: string; title: string }[]; destinations: string[] }>()
const root = useTemplateRef<HTMLElement>('root')
const { still, paused } = useSectionMotion(root)
const uid = useId()

const W = 480
const H = 300
const HUB = { x: 240, y: 150 }
const LEFT_Y = [95, 205]
const RIGHT_Y = [70, 150, 230]
const inbound = (y: number) => `M 175 ${y} C 210 ${y}, 195 ${HUB.y}, ${HUB.x - 34} ${HUB.y}`
const outbound = (y: number) => `M ${HUB.x + 34} ${HUB.y} C 300 ${HUB.y}, 300 ${y}, 360 ${y}`
const route = (from: number, to: number) =>
  `${inbound(LEFT_Y[from]!)} L ${HUB.x + 34} ${HUB.y} ${outbound(RIGHT_Y[to]!).replace(/^M [^C]+/, '')}`
const ROUTES = [
  [0, 0],
  [1, 1],
  [0, 2],
] as const
const at = (x: number, y: number) => ({ left: `${(x / W) * 100}%`, top: `${(y / H) * 100}%` })
const dests = computed(() => props.destinations.slice(0, 3))
</script>

<template>
  <div
    ref="root"
    aria-hidden="true"
    class="relative isolate overflow-hidden rounded-3xl bg-neutral-950 p-4 shadow-2xl shadow-black/20 ring-1 ring-white/10 sm:p-6"
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
    <div class="absolute -start-20 -bottom-24 -z-10 size-72 rounded-full bg-violet-600/30 blur-3xl" />

    <div dir="ltr" class="relative aspect-[8/5] w-full select-none">
      <svg :viewBox="`0 0 ${W} ${H}`" class="absolute inset-0 size-full overflow-visible">
        <defs>
          <filter :id="`${uid}-glow`" x="-200%" y="-200%" width="500%" height="500%">
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>
        <g fill="none" stroke="white" stroke-width="1.2">
          <path v-for="y in LEFT_Y" :key="`i${y}`" :d="inbound(y)" stroke-opacity="0.15" />
          <path v-for="y in RIGHT_Y" :key="`o${y}`" :d="outbound(y)" stroke-opacity="0.15" />
          <path
            v-for="y in LEFT_Y"
            :key="`id${y}`"
            :d="inbound(y)"
            stroke-opacity="0.35"
            stroke-dasharray="2 10"
            class="motion-safe:animate-dash"
          />
          <path
            v-for="y in RIGHT_Y"
            :key="`od${y}`"
            :d="outbound(y)"
            stroke-opacity="0.35"
            stroke-dasharray="2 10"
            class="motion-safe:animate-dash"
          />
        </g>
        <circle :cx="HUB.x" :cy="HUB.y" r="46" fill="none" stroke="white" stroke-opacity="0.12" />
        <template v-if="!still">
          <g v-for="([from, to], i) in ROUTES" :key="`r${i}`">
            <circle r="7" fill="#a78bfa" opacity="0" :filter="`url(#${uid}-glow)`">
              <set attributeName="opacity" to="0.6" :begin="`${i * 1.2}s`" />
              <animateMotion
                :path="route(from, to)"
                dur="3.6s"
                :begin="`${i * 1.2}s`"
                repeatCount="indefinite"
              />
            </circle>
            <circle r="2.5" fill="white" opacity="0">
              <set attributeName="opacity" to="1" :begin="`${i * 1.2}s`" />
              <animateMotion
                :path="route(from, to)"
                dur="3.6s"
                :begin="`${i * 1.2}s`"
                repeatCount="indefinite"
              />
            </circle>
          </g>
        </template>
      </svg>

      <!-- Templates -->
      <span
        v-for="(item, i) in templates"
        :key="item.title"
        class="absolute flex w-[36%] -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-xl bg-white/[0.07] p-2 text-[11px] text-white/85 ring-1 ring-white/15"
        :style="at(88, LEFT_Y[i]!)"
      >
        <span class="flex size-6 shrink-0 items-center justify-center rounded-lg bg-white/10">
          <UIcon :name="item.icon" class="size-3.5" />
        </span>
        <span class="truncate" dir="auto">{{ item.title }}</span>
      </span>

      <!-- The hub -->
      <img
        src="/brand/formalie-mark-inverse.svg"
        alt=""
        width="64"
        height="64"
        class="absolute w-[13%] -translate-x-1/2 -translate-y-1/2 rounded-[25%] shadow-[0_0_40px_rgb(255_255_255/0.25)]"
        :style="at(HUB.x, HUB.y)"
      />

      <!-- Where the data goes -->
      <span
        v-for="(icon, i) in dests"
        :key="icon"
        class="absolute flex size-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-neutral-950 shadow-lg sm:size-11"
        :style="at(390, RIGHT_Y[i]!)"
      >
        <UIcon :name="icon" class="size-4 sm:size-5" />
        <span
          v-if="!still"
          class="absolute inset-0 rounded-full ring-2 ring-white/40 motion-safe:animate-ping-soft"
          :style="{ animationDelay: `${i * 0.8}s` }"
        />
      </span>
    </div>
  </div>
</template>

<!--
  "Data on the move", the website version (docs/DESIGN.md, grown from the app's sign-in AuthFlow).
  Five live source cards send points of light through the hub (always the Formalie mark, encrypted on the way) to
  five destinations, which light up as an answer arrives: the dashboard grows a bar, the database cycles its engines.
  Response cards drift up behind the hub. On phones it stacks: three sources, the hub, three destinations.
  SVG and CSS only. Still with prefers-reduced-motion, paused off screen (useSectionMotion). Decorative: one label
  describes it for screen readers.
-->
<script setup lang="ts">
const { t, locale } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { still, paused } = useSectionMotion(root)
const uid = useId()

// Desktop drawing space; cards and pills sit at the same points (in percent), so everything scales together.
const W = 720
const H = 480
const HUB = { x: 360, y: 240 }
const SOURCE_X = 100
const TARGET_X = 620
/** Half a card's width in the drawing (cards are 26% wide). */
const HALF = 94
const ROWS = [48, 144, 240, 336, 432]

const SOURCES = [
  { key: 'link', icon: 'i-lucide-link' },
  { key: 'embed', icon: 'i-lucide-code-xml' },
  { key: 'qr', icon: 'i-lucide-qr-code' },
  { key: 'api', icon: 'i-lucide-braces' },
  { key: 'app', icon: 'i-lucide-smartphone' },
] as const
const TARGETS = [
  { key: 'database', icon: 'i-lucide-database' },
  { key: 'webhooks', icon: 'i-lucide-webhook' },
  { key: 'dashboard', icon: 'i-lucide-chart-column' },
  { key: 'email', icon: 'i-lucide-mail-check' },
  { key: 'storage', icon: 'i-lucide-hard-drive' },
] as const
/** Where each source's answer goes (crossed, so it never looks like five parallel lanes). */
const ROUTES = [2, 0, 4, 1, 3]
const CYCLE = 5 // seconds from source to destination
const STAGGER = CYCLE / ROUTES.length
/** The dashboard grows a bar when the form link's answer arrives (route 0 starts at 0 s). */
const DASHBOARD_DELAY = `${ROUTES.indexOf(2) * STAGGER}s`

const inbound = (y: number) =>
  `M ${SOURCE_X + HALF} ${y} C ${SOURCE_X + 190} ${y}, ${HUB.x - 120} ${HUB.y}, ${HUB.x - 46} ${HUB.y}`
const outbound = (y: number) =>
  `M ${HUB.x + 46} ${HUB.y} C ${HUB.x + 120} ${HUB.y}, ${TARGET_X - 190} ${y}, ${TARGET_X - HALF} ${y}`
const route = (from: number, to: number) =>
  `${inbound(ROWS[from]!)} L ${HUB.x + 46} ${HUB.y} ${outbound(ROWS[to]!).replace(/^M [^C]+/, '')}`
const at = (x: number, y: number, w = W, h = H) => ({ left: `${(x / w) * 100}%`, top: `${(y / h) * 100}%` })

// Phones: top to bottom in a narrow drawing.
const MW = 360
const MH = 420
const MHUB = { x: 180, y: 210 }
const MCOLS = [60, 180, 300]
const MSOURCES = [SOURCES[0], SOURCES[2], SOURCES[3]]
const MTARGETS = [TARGETS[0], TARGETS[2], TARGETS[3]]
const MROUTES = [1, 2, 0]
const mInbound = (x: number) => `M ${x} 62 C ${x} 130, ${MHUB.x} 120, ${MHUB.x} ${MHUB.y - 40}`
const mOutbound = (x: number) => `M ${MHUB.x} ${MHUB.y + 40} C ${MHUB.x} 300, ${x} 290, ${x} 358`
const mRoute = (from: number, to: number) =>
  `${mInbound(MCOLS[from]!)} L ${MHUB.x} ${MHUB.y + 40} ${mOutbound(MCOLS[to]!).replace(/^M [^C]+/, '')}`
const M_STAGGER = CYCLE / MROUTES.length

/** Faint response cards drifting up behind the hub (answers being collected). */
const CARDS = [
  { x: 262, y: 104, w: 88, delay: 0, initial: 'A' },
  { x: 462, y: 128, w: 76, delay: 2.4, initial: 'K' },
  { x: 268, y: 380, w: 80, delay: 1.2, initial: 'M' },
  { x: 458, y: 364, w: 92, delay: 3.6, initial: 'S' },
]

/** The database destination cycles through the engines a workspace can connect. */
const ENGINES = [
  'i-simple-icons-mysql',
  'i-simple-icons-postgresql',
  'i-simple-icons-mariadb',
  'i-simple-icons-microsoftsqlserver',
  'i-simple-icons-oracle',
]

/** The pattern of the little QR code (decorative). */
const QR = ['1110101', '1010010', '1110111', '0001010', '1011101', '0100101', '1101011']

// Illustrative counters that tick softly while the panel is on screen (labelled as an example).
const counts = reactive({ responses: 12480, database: 9316, countries: 38 })
const format = (value: number) => new Intl.NumberFormat(locale.value).format(value)
useIntervalFn(() => {
  if (still.value || paused.value) return
  const add = 1 + Math.floor(Math.random() * 3)
  counts.responses += add
  counts.database += Math.max(1, add - 1)
}, 1600)
</script>

<template>
  <div ref="root" :class="{ 'motion-paused': paused }">
    <div
      role="img"
      :aria-label="t('home.flow.label')"
      class="relative isolate overflow-hidden rounded-3xl bg-neutral-950 p-4 text-white shadow-2xl shadow-black/20 ring-1 ring-white/10 sm:p-6"
    >
      <!-- Faint grid and one violet glow, as in the app's sign-in panel -->
      <div
        aria-hidden="true"
        class="absolute inset-0 -z-10 opacity-60"
        style="
          background-image:
            linear-gradient(rgb(255 255 255 / 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgb(255 255 255 / 0.05) 1px, transparent 1px);
          background-size: 32px 32px;
          mask-image: radial-gradient(ellipse at center, black 40%, transparent 85%);
        "
      />
      <div
        aria-hidden="true"
        class="absolute -start-24 -bottom-32 -z-10 size-96 rounded-full bg-violet-600/25 blur-3xl"
      />
      <div
        aria-hidden="true"
        class="absolute -end-20 -top-24 -z-10 size-72 rounded-full bg-white/5 blur-3xl"
      />

      <!-- Desktop and tablet: sources on the left, the hub, destinations on the right -->
      <div aria-hidden="true" dir="ltr" class="relative hidden aspect-[3/2] w-full select-none sm:block">
        <div
          v-for="(card, i) in CARDS"
          :key="`card-${i}`"
          class="absolute flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-lg bg-white/[0.04] p-1.5 ring-1 ring-white/10 motion-safe:animate-drift"
          :style="{
            ...at(card.x, card.y),
            width: `${(card.w / W) * 100}%`,
            animationDelay: `${card.delay}s`,
          }"
        >
          <span
            class="flex size-4 shrink-0 items-center justify-center rounded-full bg-white/15 text-[8px] font-semibold"
          >
            {{ card.initial }}
          </span>
          <span class="flex min-w-0 flex-1 flex-col gap-1">
            <span class="h-1 w-3/4 rounded-full bg-white/25" />
            <span class="h-1 w-1/2 rounded-full bg-white/15" />
          </span>
        </div>

        <svg :viewBox="`0 0 ${W} ${H}`" class="absolute inset-0 size-full overflow-visible">
          <defs>
            <filter :id="`${uid}-glow`" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur stdDeviation="3" />
            </filter>
            <radialGradient :id="`${uid}-halo`" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stop-color="#ffffff" stop-opacity="0.3" />
              <stop offset="60%" stop-color="#7c3aed" stop-opacity="0.12" />
              <stop offset="100%" stop-color="#7c3aed" stop-opacity="0" />
            </radialGradient>
          </defs>

          <g fill="none" stroke="white" stroke-width="1.2">
            <path v-for="(y, i) in ROWS" :key="`in-${i}`" :d="inbound(y)" stroke-opacity="0.14" />
            <path v-for="(y, i) in ROWS" :key="`out-${i}`" :d="outbound(y)" stroke-opacity="0.14" />
            <path
              v-for="(y, i) in ROWS"
              :key="`in-dash-${i}`"
              :d="inbound(y)"
              stroke-opacity="0.35"
              stroke-dasharray="2 10"
              class="motion-safe:animate-dash"
            />
            <path
              v-for="(y, i) in ROWS"
              :key="`out-dash-${i}`"
              :d="outbound(y)"
              stroke-opacity="0.35"
              stroke-dasharray="2 10"
              class="motion-safe:animate-dash"
            />
          </g>

          <circle :cx="HUB.x" :cy="HUB.y" r="120" :fill="`url(#${uid}-halo)`" />
          <circle :cx="HUB.x" :cy="HUB.y" r="56" fill="none" stroke="white" stroke-opacity="0.12" />
          <circle
            :cx="HUB.x"
            :cy="HUB.y"
            r="74"
            fill="none"
            stroke="white"
            stroke-opacity="0.06"
            stroke-dasharray="3 6"
          />
          <!-- A soft pulse each time an answer passes through the hub -->
          <circle
            v-if="!still"
            :cx="HUB.x"
            :cy="HUB.y"
            r="48"
            fill="none"
            stroke="#ffffff"
            stroke-width="1.5"
          >
            <animate attributeName="r" values="48;96" :dur="`${STAGGER}s`" repeatCount="indefinite" />
            <animate
              attributeName="stroke-opacity"
              values="0.5;0"
              :dur="`${STAGGER}s`"
              repeatCount="indefinite"
            />
          </circle>

          <template v-if="!still">
            <g v-for="(to, from) in ROUTES" :key="`dot-${from}`">
              <circle r="8" fill="#a78bfa" opacity="0" :filter="`url(#${uid}-glow)`">
                <set attributeName="opacity" to="0.6" :begin="`${from * STAGGER}s`" />
                <animateMotion
                  :path="route(from, to)"
                  :dur="`${CYCLE}s`"
                  :begin="`${from * STAGGER}s`"
                  repeatCount="indefinite"
                  calcMode="spline"
                  keyTimes="0;1"
                  keySplines="0.45 0 0.55 1"
                />
              </circle>
              <circle r="3" fill="white" opacity="0">
                <set attributeName="opacity" to="1" :begin="`${from * STAGGER}s`" />
                <animateMotion
                  :path="route(from, to)"
                  :dur="`${CYCLE}s`"
                  :begin="`${from * STAGGER}s`"
                  repeatCount="indefinite"
                  calcMode="spline"
                  keyTimes="0;1"
                  keySplines="0.45 0 0.55 1"
                />
              </circle>
              <!-- The destination lights up as the answer arrives -->
              <rect
                :x="TARGET_X - HALF"
                :y="ROWS[to]! - 22"
                :width="HALF * 2"
                height="44"
                rx="22"
                fill="none"
                stroke="#ffffff"
                stroke-width="1.5"
                opacity="0"
              >
                <animate
                  attributeName="opacity"
                  values="0;0;0.9;0"
                  keyTimes="0;0.86;0.93;1"
                  :dur="`${CYCLE}s`"
                  :begin="`${from * STAGGER}s`"
                  repeatCount="indefinite"
                />
              </rect>
            </g>
          </template>
        </svg>

        <!-- The hub: always the Formalie mark -->
        <div
          class="absolute flex w-[13%] -translate-x-1/2 -translate-y-1/2 flex-col items-center"
          :style="at(HUB.x, HUB.y)"
        >
          <span class="relative block w-full">
            <img
              src="/brand/formalie-mark-inverse.svg"
              alt=""
              width="64"
              height="64"
              class="block w-full rounded-[25%] shadow-[0_0_48px_rgb(255_255_255/0.28)]"
            />
            <span
              class="absolute -end-2 -bottom-2 flex size-6 items-center justify-center rounded-full bg-neutral-950 text-white ring-2 ring-white"
            >
              <UIcon name="i-lucide-lock-keyhole" class="size-3" />
            </span>
          </span>
        </div>
        <span
          class="absolute -translate-x-1/2 text-[11px] whitespace-nowrap text-white/60"
          :style="at(HUB.x, HUB.y + 64)"
        >
          {{ t('home.flow.hub') }}
        </span>

        <!-- Sources: small live cards -->
        <div
          v-for="(item, i) in SOURCES"
          :key="item.key"
          class="absolute flex w-[26%] -translate-x-1/2 -translate-y-1/2 flex-col gap-1.5 rounded-xl bg-white/[0.06] p-2 text-white/85 ring-1 ring-white/15 backdrop-blur-sm"
          :style="at(SOURCE_X, ROWS[i]!)"
        >
          <span class="flex items-center gap-1.5 text-[11px] font-medium">
            <span class="flex size-5 shrink-0 items-center justify-center rounded-full bg-white/10">
              <UIcon :name="item.icon" class="size-3" />
            </span>
            <span class="truncate">{{ t(`home.flow.sources.${item.key}`) }}</span>
          </span>

          <!-- Form link: a field being filled in -->
          <span
            v-if="item.key === 'link'"
            class="flex items-center gap-1 rounded-md bg-white/5 px-1.5 py-1 text-[10px]"
          >
            <span class="text-white/45">{{ t('home.flow.nameField') }}</span>
            <span class="inline-flex min-w-0 items-center">
              <span class="inline-block max-w-full overflow-hidden whitespace-nowrap motion-safe:animate-type"
                >Amara Okafor</span
              >
              <span class="ms-px inline-block h-2.5 w-px bg-white motion-safe:animate-caret" />
            </span>
          </span>

          <!-- Website embed: a tiny browser with the form inside -->
          <span v-else-if="item.key === 'embed'" class="flex flex-col gap-1 rounded-md bg-white/5 p-1">
            <span class="flex items-center gap-0.5">
              <span class="size-1 rounded-full bg-white/30" />
              <span class="size-1 rounded-full bg-white/30" />
              <span class="size-1 rounded-full bg-white/30" />
              <span class="ms-1 h-1 w-1/2 rounded-full bg-white/15" />
            </span>
            <span class="h-1 w-3/4 rounded-full bg-white/25" />
          </span>

          <!-- QR code: scanned on the spot -->
          <span v-else-if="item.key === 'qr'" class="flex items-center gap-2">
            <span class="relative grid size-6 grid-cols-7 gap-px overflow-hidden rounded-sm bg-white p-0.5">
              <template v-for="(row, r) in QR" :key="`qr-${r}`">
                <span
                  v-for="(cell, c) in row.split('')"
                  :key="`qr-${r}-${c}`"
                  :class="cell === '1' ? 'bg-neutral-950' : 'bg-white'"
                />
              </template>
              <span
                class="absolute inset-x-0 h-px bg-violet-500 shadow-[0_0_6px_#8b5cf6] motion-safe:animate-scan"
              />
            </span>
            <span class="h-1 flex-1 rounded-full bg-white/15" />
          </span>

          <!-- API: a request on its way -->
          <span
            v-else-if="item.key === 'api'"
            class="flex items-center justify-between gap-1 rounded-md bg-white/5 px-1.5 py-1 font-mono text-[9px]"
          >
            <span class="truncate text-white/70">POST /responses</span>
            <span class="rounded bg-emerald-400/15 px-1 text-emerald-300">201</span>
          </span>

          <!-- Mobile app: calls the API -->
          <span v-else class="flex items-center gap-1.5 text-[10px] text-white/50">
            <span class="relative flex size-2">
              <span
                class="absolute inline-flex size-full rounded-full bg-emerald-400 motion-safe:animate-ping-soft"
              />
              <span class="relative inline-flex size-2 rounded-full bg-emerald-400" />
            </span>
            {{ t('home.flow.viaApi') }}
          </span>
        </div>

        <!-- Destinations: they light up as answers arrive -->
        <div
          v-for="(item, i) in TARGETS"
          :key="item.key"
          class="absolute flex w-[26%] -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 rounded-full bg-white/[0.06] py-1.5 ps-1.5 pe-2.5 text-[11px] text-white/85 ring-1 ring-white/15 backdrop-blur-sm"
          :style="at(TARGET_X, ROWS[i]!)"
        >
          <span
            class="flex size-6 shrink-0 items-center justify-center rounded-full bg-white text-neutral-950"
          >
            <UIcon :name="item.icon" class="size-3.5" />
          </span>
          <span class="min-w-0 flex-1 truncate font-medium">{{ t(`home.flow.targets.${item.key}`) }}</span>

          <span v-if="item.key === 'database'" class="relative size-3.5 shrink-0">
            <UIcon
              v-for="(engine, e) in ENGINES"
              :key="engine"
              :name="engine"
              class="absolute inset-0 size-3.5 text-white/80 motion-safe:animate-cycle"
              :class="{ 'opacity-0 motion-reduce:opacity-0': e > 0, 'motion-reduce:opacity-100': e === 0 }"
              :style="{ animationDelay: `${e * 2}s` }"
            />
          </span>
          <span v-else-if="item.key === 'webhooks'" class="shrink-0 font-mono text-[9px] text-emerald-300"
            >200</span
          >
          <span v-else-if="item.key === 'dashboard'" class="flex h-3.5 shrink-0 items-end gap-px">
            <span class="h-[40%] w-1 rounded-sm bg-white/40" />
            <span class="h-[65%] w-1 rounded-sm bg-white/40" />
            <span class="h-[50%] w-1 rounded-sm bg-white/40" />
            <span
              class="h-full w-1 origin-bottom rounded-sm bg-violet-400 motion-safe:animate-bar"
              :style="{ animationDelay: DASHBOARD_DELAY }"
            />
          </span>
          <UIcon
            v-else-if="item.key === 'storage'"
            name="i-lucide-lock-keyhole"
            class="size-3 shrink-0 text-white/60"
          />
          <span v-else class="size-1.5 shrink-0 rounded-full bg-violet-400" />
        </div>
      </div>

      <!-- Phones: top to bottom -->
      <div aria-hidden="true" dir="ltr" class="relative aspect-[6/7] w-full select-none sm:hidden">
        <svg :viewBox="`0 0 ${MW} ${MH}`" class="absolute inset-0 size-full overflow-visible">
          <g fill="none" stroke="white" stroke-width="1.2">
            <path v-for="(x, i) in MCOLS" :key="`m-in-${i}`" :d="mInbound(x)" stroke-opacity="0.16" />
            <path v-for="(x, i) in MCOLS" :key="`m-out-${i}`" :d="mOutbound(x)" stroke-opacity="0.16" />
            <path
              v-for="(x, i) in MCOLS"
              :key="`m-in-dash-${i}`"
              :d="mInbound(x)"
              stroke-opacity="0.35"
              stroke-dasharray="2 10"
              class="motion-safe:animate-dash"
            />
            <path
              v-for="(x, i) in MCOLS"
              :key="`m-out-dash-${i}`"
              :d="mOutbound(x)"
              stroke-opacity="0.35"
              stroke-dasharray="2 10"
              class="motion-safe:animate-dash"
            />
          </g>
          <circle :cx="MHUB.x" :cy="MHUB.y" r="80" :fill="`url(#${uid}-halo)`" />
          <template v-if="!still">
            <g v-for="(to, from) in MROUTES" :key="`m-dot-${from}`">
              <circle r="7" fill="#a78bfa" opacity="0" :filter="`url(#${uid}-glow)`">
                <set attributeName="opacity" to="0.6" :begin="`${from * M_STAGGER}s`" />
                <animateMotion
                  :path="mRoute(from, to)"
                  :dur="`${CYCLE}s`"
                  :begin="`${from * M_STAGGER}s`"
                  repeatCount="indefinite"
                />
              </circle>
              <circle r="3" fill="white" opacity="0">
                <set attributeName="opacity" to="1" :begin="`${from * M_STAGGER}s`" />
                <animateMotion
                  :path="mRoute(from, to)"
                  :dur="`${CYCLE}s`"
                  :begin="`${from * M_STAGGER}s`"
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          </template>
        </svg>

        <span
          v-for="(item, i) in MSOURCES"
          :key="`m-${item!.key}`"
          class="absolute flex w-[31%] -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1 rounded-xl bg-white/[0.06] px-1 py-2 text-center text-[10px] text-white/85 ring-1 ring-white/15"
          :style="at(MCOLS[i]!, 36, MW, MH)"
        >
          <UIcon :name="item!.icon" class="size-4" />
          <span class="w-full truncate">{{ t(`home.flow.sources.${item!.key}`) }}</span>
        </span>

        <div
          class="absolute flex w-[20%] -translate-x-1/2 -translate-y-1/2 flex-col items-center"
          :style="at(MHUB.x, MHUB.y, MW, MH)"
        >
          <span class="relative block w-full">
            <img
              src="/brand/formalie-mark-inverse.svg"
              alt=""
              width="64"
              height="64"
              class="block w-full rounded-[25%] shadow-[0_0_40px_rgb(255_255_255/0.25)]"
            />
            <span
              class="absolute -end-1.5 -bottom-1.5 flex size-5 items-center justify-center rounded-full bg-neutral-950 text-white ring-2 ring-white"
            >
              <UIcon name="i-lucide-lock-keyhole" class="size-2.5" />
            </span>
          </span>
        </div>

        <span
          v-for="(item, i) in MTARGETS"
          :key="`m-${item!.key}`"
          class="absolute flex w-[31%] -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1 rounded-xl bg-white/[0.06] px-1 py-2 text-center text-[10px] text-white/85 ring-1 ring-white/15"
          :style="at(MCOLS[i]!, 384, MW, MH)"
        >
          <span class="flex size-6 items-center justify-center rounded-full bg-white text-neutral-950">
            <UIcon :name="item!.icon" class="size-3.5" />
          </span>
          <span class="w-full truncate">{{ t(`home.flow.targets.${item!.key}`) }}</span>
        </span>
      </div>
    </div>

    <!-- Counters under the panel, clearly an example -->
    <dl class="mt-4 grid grid-cols-3 gap-2 sm:gap-4">
      <div class="rounded-xl bg-default/70 p-3 ring-1 ring-default backdrop-blur">
        <dt class="text-xs text-muted">{{ t('home.flow.counters.responses') }}</dt>
        <dd class="mt-1 text-lg font-semibold tabular-nums text-highlighted sm:text-xl">
          {{ format(counts.responses) }}
        </dd>
      </div>
      <div class="rounded-xl bg-default/70 p-3 ring-1 ring-default backdrop-blur">
        <dt class="text-xs text-muted">{{ t('home.flow.counters.database') }}</dt>
        <dd class="mt-1 text-lg font-semibold tabular-nums text-highlighted sm:text-xl">
          {{ format(counts.database) }}
        </dd>
      </div>
      <div class="rounded-xl bg-default/70 p-3 ring-1 ring-default backdrop-blur">
        <dt class="text-xs text-muted">{{ t('home.flow.counters.countries') }}</dt>
        <dd class="mt-1 text-lg font-semibold tabular-nums text-highlighted sm:text-xl">
          {{ format(counts.countries) }}
        </dd>
      </div>
    </dl>
    <p class="mt-2 text-end text-xs text-dimmed">{{ t('home.flow.counters.note') }}</p>
  </div>
</template>

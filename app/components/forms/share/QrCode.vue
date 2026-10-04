<!--
  QR code for a form link (uqr encodes; we draw, no v-html). Two styles:
    branded, a card: "scan to open" on top; the QR with the organisation's logo (or initials) in
              the middle, Formalie's mark for workspaces without their own subdomain; below, the
              organisation and the form name; a footer with the Formalie mark and the short address
    plain:  the QR alone with its quiet zone
  The preview, the SVG and the PNG come from the same markup (svgText), so downloads look the same.
  Error correction is "H" (30%) so the centre badge never breaks scanning.
-->
<script setup lang="ts">
import { encode } from 'uqr'

const props = withDefaults(
  defineProps<{
    value: string
    color?: string
    label: string
    branded?: boolean
    /** Organisation shown on the card; null = Formalie (no own subdomain). */
    org?: { name: string; logo: string | null } | null
    formName?: string
    host?: string
    scanLabel?: string
  }>(),
  { color: '#18181b', branded: true, org: null, formName: '', host: '', scanLabel: '' },
)

const INK = '#18181b'
const MUTED = '#71717a'
const FONT = "Manrope, 'Segoe UI', system-ui, sans-serif"

const matrix = computed(() => encode(props.value, { ecc: 'H', border: 0 }).data)
const n = computed(() => matrix.value.length)

// ── Geometry ────────────────────────────────────────────────────────────────────────
const W = 360
const QR = 248 // QR box (branded card)
const plainMargin = 4
const cardQrX = (W - QR) / 2
const cardQrY = 64
const moduleSize = computed(() => (props.branded ? QR / n.value : 1))
/** Centre badge: about a fifth of the code, in whole modules, always odd so it sits centred. */
const badgeModules = computed(() => {
  const m = Math.round(n.value * 0.22)
  return m % 2 ? m : m + 1
})
const badgeStart = computed(() => (n.value - badgeModules.value) / 2)

const path = computed(() => {
  const offset = props.branded ? 0 : plainMargin
  const skip = props.branded
  const b0 = badgeStart.value - 1
  const b1 = badgeStart.value + badgeModules.value
  let d = ''
  matrix.value.forEach((row, y) =>
    row.forEach((dark, x) => {
      if (!dark) return
      if (skip && x >= b0 && x <= b1 && y >= b0 && y <= b1) return
      d += `M${x + offset} ${y + offset}h1v1h-1z`
    }),
  )
  return d
})

// ── Text ────────────────────────────────────────────────────────────────────────────
/** Up to two lines of about 30 characters, cut at words. */
function wrap(text: string, max = 30): string[] {
  const words = text.trim().split(/\s+/)
  const lines: string[] = ['']
  for (const word of words) {
    const line = lines.at(-1)!
    if ((line + ' ' + word).trim().length <= max) lines[lines.length - 1] = (line + ' ' + word).trim()
    else if (lines.length < 2) lines.push(word)
    else {
      lines[1] = `${lines[1]!.slice(0, max - 1).trimEnd()}…`
      break
    }
  }
  return lines.filter(Boolean)
}
const orgName = computed(() => props.org?.name ?? 'Formalie')
const formLines = computed(() => wrap(props.formName))
const initials = computed(() =>
  (props.org?.name ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join(''),
)
const orgY = computed(() => cardQrY + QR + 38)
const formY = computed(() => orgY.value + 24)
const footerY = computed(() => formY.value + (formLines.value.length - 1) * 19 + 34)
const H = computed(() => footerY.value + 40)

// Centre badge in card units.
const badge = computed(() => {
  const size = (badgeModules.value + 2) * moduleSize.value
  return { x: cardQrX + (badgeStart.value - 1) * moduleSize.value, y: cardQrY + (badgeStart.value - 1) * moduleSize.value, size }
})

/** The Formalie mark (lucide file-check-2 on a dark rounded square), at x / y with size s. */
const markPaths = ['M4 22h14a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v4', 'M14 2v4a2 2 0 0 0 2 2h4', 'm3 15 2 2 4-4']

// ── Export ──────────────────────────────────────────────────────────────────────────
const svgRef = useTemplateRef<SVGSVGElement>('svg')
/** Standalone SVG text; `logoData` replaces the logo URL so the file has no outside links. */
function svgText(logoData?: string | null) {
  const node = svgRef.value?.cloneNode(true) as SVGSVGElement | undefined
  if (!node) return ''
  node.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  node.removeAttribute('class')
  const image = node.querySelector('image')
  if (image) {
    if (logoData) image.setAttribute('href', logoData)
    else image.remove()
  }
  return new XMLSerializer().serializeToString(node)
}
defineExpose({ svgText, width: () => (props.branded ? W : n.value + plainMargin * 2), height: () => (props.branded ? H.value : n.value + plainMargin * 2) })
</script>

<template>
  <!-- Branded card -->
  <svg
    v-if="branded"
    ref="svg"
    :viewBox="`0 0 ${W} ${H}`"
    role="img"
    :aria-label="label"
    class="block h-auto w-full"
    :font-family="FONT"
  >
    <rect x="0.5" y="0.5" :width="W - 1" :height="H - 1" rx="22" fill="#ffffff" stroke="#e4e4e7" />
    <text :x="W / 2" y="40" text-anchor="middle" font-size="12" font-weight="600" letter-spacing="1.5" :fill="color">{{ scanLabel.toUpperCase() }}</text>

    <g :transform="`translate(${cardQrX} ${cardQrY}) scale(${moduleSize})`">
      <path :d="path" :fill="color" shape-rendering="crispEdges" />
    </g>

    <!-- Centre: organisation logo, its initials, or Formalie's mark -->
    <rect :x="badge.x" :y="badge.y" :width="badge.size" :height="badge.size" :rx="badge.size * 0.22" fill="#ffffff" />
    <template v-if="org && org.logo">
      <image :href="org.logo" :x="badge.x + badge.size * 0.12" :y="badge.y + badge.size * 0.12" :width="badge.size * 0.76" :height="badge.size * 0.76" preserveAspectRatio="xMidYMid meet" />
    </template>
    <template v-else-if="org">
      <rect :x="badge.x + badge.size * 0.1" :y="badge.y + badge.size * 0.1" :width="badge.size * 0.8" :height="badge.size * 0.8" :rx="badge.size * 0.18" :fill="color" />
      <text :x="badge.x + badge.size / 2" :y="badge.y + badge.size / 2" text-anchor="middle" dominant-baseline="central" :font-size="badge.size * 0.34" font-weight="700" fill="#ffffff">{{ initials }}</text>
    </template>
    <g v-else :transform="`translate(${badge.x + badge.size * 0.1} ${badge.y + badge.size * 0.1})`">
      <rect :width="badge.size * 0.8" :height="badge.size * 0.8" :rx="badge.size * 0.18" :fill="INK" />
      <g :transform="`translate(${badge.size * 0.16} ${badge.size * 0.16}) scale(${(badge.size * 0.48) / 24})`" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path v-for="d in markPaths" :key="d" :d="d" />
      </g>
    </g>

    <!-- Organisation and form -->
    <text :x="W / 2" :y="orgY" text-anchor="middle" font-size="18" font-weight="700" :fill="INK">{{ orgName }}</text>
    <text v-for="(line, i) in formLines" :key="i" :x="W / 2" :y="formY + i * 19" text-anchor="middle" font-size="14" :fill="MUTED">{{ line }}</text>

    <!-- Footer: Formalie on one side, the short address on the other -->
    <line x1="28" :x2="W - 28" :y1="footerY - 18" :y2="footerY - 18" stroke="#e4e4e7" />
    <g :transform="`translate(28 ${footerY - 6})`">
      <rect width="18" height="18" rx="5" :fill="INK" />
      <g transform="translate(3.5 3.5) scale(0.46)" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path v-for="d in markPaths" :key="d" :d="d" />
      </g>
      <text x="25" y="13.5" font-size="12.5" font-weight="700" :fill="INK">Formalie</text>
    </g>
    <text :x="W - 28" :y="footerY + 7.5" text-anchor="end" font-size="11" :fill="MUTED">{{ host }}</text>
  </svg>

  <!-- Plain QR -->
  <svg
    v-else
    ref="svg"
    :viewBox="`0 0 ${n + plainMargin * 2} ${n + plainMargin * 2}`"
    shape-rendering="crispEdges"
    role="img"
    :aria-label="label"
    class="block h-auto w-full"
  >
    <rect width="100%" height="100%" fill="#ffffff" />
    <path :d="path" :fill="color" />
  </svg>
</template>

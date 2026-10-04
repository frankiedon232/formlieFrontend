<!--
  Preview page (F10 M3): the form inside a device. Desktop = a browser window with the form's
  address; tablet and phone = a device at its real screen size (portrait or turned sideways).
  The form is laid out at the device's true width (container queries), then the whole device is
  scaled down to fit the space, so what you see is what that screen shows.
-->
<script setup lang="ts">
const props = defineProps<{ device: 'desktop' | 'tablet' | 'phone'; landscape?: boolean; address?: string }>()
const { t } = useI18n()

const stage = useTemplateRef<HTMLElement>('stage')
const { width, height } = useElementSize(stage)

/** Real screen sizes in CSS pixels (portrait), a common tablet and phone. */
const SCREENS = { tablet: [820, 1180], phone: [390, 844] } as const
const BEZEL = { tablet: 14, phone: 12 } as const
const DESKTOP_MIN = 1024
const BAR = 40

const box = computed(() => {
  if (props.device === 'desktop') {
    // At least a small laptop width; narrower spaces show it scaled down.
    const outerW = Math.max(width.value, DESKTOP_MIN)
    const scale = width.value ? Math.min(1, width.value / outerW) : 0
    return { outerW, outerH: scale ? height.value / scale : 0, scale }
  }
  const [w, h] = SCREENS[props.device]
  const [screenW, screenH] = props.landscape ? [h, w] : [w, h]
  const outerW = screenW + BEZEL[props.device] * 2
  const outerH = screenH + BEZEL[props.device] * 2
  const scale = width.value ? Math.min(1, width.value / outerW, height.value / outerH) : 0
  return { outerW, outerH, scale }
})
const percent = computed(() => Math.round(box.value.scale * 100))
</script>

<template>
  <div ref="stage" class="relative flex h-full w-full justify-center overflow-hidden">
    <div v-if="box.scale" class="shrink-0" :style="{ width: `${box.outerW * box.scale}px`, height: `${box.outerH * box.scale}px` }">
      <div
        class="origin-top-left"
        :style="{ width: `${box.outerW}px`, height: `${box.outerH}px`, transform: `scale(${box.scale})` }"
      >
        <!-- One frame for every device, so switching keeps what was typed: desktop = a browser window,
             tablet / phone = the device with its screen. -->
        <div
          class="relative flex h-full flex-col"
          :class="
            device === 'desktop'
              ? 'overflow-hidden rounded-lg border border-default bg-default'
              : ['bg-neutral-900 shadow-xl ring-1 ring-(--ui-border-accented) dark:bg-neutral-700', device === 'phone' ? 'rounded-[3rem]' : 'rounded-[2.25rem]']
          "
          :style="device === 'desktop' ? undefined : { padding: `${BEZEL[device]}px` }"
        >
          <div v-if="device === 'desktop'" class="flex shrink-0 items-center gap-3 border-b border-default bg-elevated px-3" :style="{ height: `${BAR}px` }">
            <span class="flex gap-1.5" aria-hidden="true">
              <span v-for="n in 3" :key="n" class="size-2.5 rounded-full bg-accented" />
            </span>
            <span class="mx-auto flex max-w-md min-w-0 flex-1 items-center gap-1.5 rounded-md border border-default bg-default px-3 py-1 text-xs text-muted">
              <UIcon name="i-lucide-lock" class="size-3 shrink-0" />
              <span class="truncate" dir="ltr">{{ address }}</span>
            </span>
            <span class="w-10" aria-hidden="true" />
          </div>
          <!-- Camera, in the top bezel (the side bezel when turned). -->
          <span
            v-else
            class="absolute size-1.5 rounded-full bg-neutral-600"
            :class="landscape ? 'start-1 top-1/2 -translate-y-1/2' : 'start-1/2 top-1 -translate-x-1/2 rtl:translate-x-1/2'"
            aria-hidden="true"
          />
          <div
            class="min-h-0 flex-1 overflow-x-hidden overflow-y-auto bg-default @container"
            :class="device === 'phone' ? 'rounded-[2.25rem]' : device === 'tablet' ? 'rounded-[1.5rem]' : ''"
          >
            <slot />
          </div>
        </div>
      </div>
    </div>
    <span v-if="percent < 100" class="absolute end-2 bottom-2 rounded-md bg-default/80 px-1.5 py-0.5 text-[11px] text-muted tabular-nums ring-1 ring-(--ui-border)">
      {{ t('preview.scale', { percent }) }}
    </span>
  </div>
</template>

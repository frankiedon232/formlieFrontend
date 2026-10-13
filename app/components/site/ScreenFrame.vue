<script setup lang="ts">
// A real, cropped and watermarked app screen (docs/SECURITY.md) in a browser frame with a soft glow
// (docs/DESIGN.md "Using the screenshots"). The dark version shows in dark mode when there is one.
const props = withDefaults(
  defineProps<{ shot: Screenshot; alt: string; sizes?: string; eager?: boolean; tilt?: boolean }>(),
  { sizes: 'sm:100vw md:90vw lg:640px', eager: false, tilt: false },
)
const loading = computed(() => (props.eager ? 'eager' : 'lazy'))
</script>

<template>
  <div class="relative">
    <div aria-hidden="true" class="absolute -inset-6 rounded-[2rem] bg-violet-500/10 blur-2xl" />
    <figure
      class="relative overflow-hidden rounded-2xl bg-elevated shadow-2xl shadow-black/10 ring-1 ring-default transition-transform duration-500"
      :class="{ 'lg:-rotate-1 motion-safe:hover:rotate-0': tilt }"
    >
      <div aria-hidden="true" class="flex items-center gap-1.5 border-b border-default px-3 py-2">
        <span class="size-2.5 rounded-full bg-accented" />
        <span class="size-2.5 rounded-full bg-accented" />
        <span class="size-2.5 rounded-full bg-accented" />
      </div>
      <NuxtImg
        :src="`/screenshots/${shot.file}.webp`"
        :alt="alt"
        :width="shot.width"
        :height="shot.height"
        :sizes="sizes"
        :loading="loading"
        class="block h-auto w-full"
        :class="{ 'dark:hidden': shot.dark }"
      />
      <NuxtImg
        v-if="shot.dark"
        :src="`/screenshots/${shot.file}-dark.webp`"
        :alt="alt"
        :width="shot.width"
        :height="shot.height"
        :sizes="sizes"
        loading="lazy"
        class="hidden h-auto w-full dark:block"
      />
    </figure>
  </div>
</template>

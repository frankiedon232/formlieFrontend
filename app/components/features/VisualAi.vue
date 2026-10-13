<script setup lang="ts">
// The AI assistant at work (drawn, there is no screen to show): a prompt is typed, the assistant thinks, and a
// form draft builds itself question by question. Loops; still for reduced motion; paused off screen.
const { t } = useI18n()
const root = useTemplateRef<HTMLElement>('root')
const { paused } = useSectionMotion(root)

// The drafted questions (sample content, shown as bars with an icon).
const FIELDS = [
  { icon: 'i-lucide-user', width: 'w-2/5' },
  { icon: 'i-lucide-mail', width: 'w-1/2' },
  { icon: 'i-lucide-phone', width: 'w-1/3' },
  { icon: 'i-lucide-briefcase', width: 'w-3/5' },
  { icon: 'i-lucide-upload', width: 'w-1/3' },
]
</script>

<template>
  <div
    ref="root"
    aria-hidden="true"
    class="relative isolate overflow-hidden rounded-3xl bg-neutral-950 p-5 text-white shadow-2xl shadow-black/20 ring-1 ring-white/10 sm:p-8"
    :class="{ 'motion-paused': paused }"
  >
    <div class="absolute -end-24 -top-24 -z-10 size-80 rounded-full bg-violet-600/30 blur-3xl" />

    <!-- The prompt -->
    <div class="flex items-start gap-3">
      <span
        class="flex size-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold"
        >EC</span
      >
      <div
        class="min-w-0 flex-1 rounded-2xl rounded-ss-sm bg-white/[0.07] px-4 py-3 text-sm ring-1 ring-white/10"
      >
        <span
          class="inline-block max-w-full overflow-hidden align-bottom whitespace-nowrap motion-safe:animate-[type_8s_steps(40,end)_infinite]"
        >
          {{ t('features.ai-assistant.prompt') }}
        </span>
        <span class="ms-px inline-block h-4 w-px bg-white align-middle motion-safe:animate-caret" />
      </div>
    </div>

    <!-- The assistant answers with a draft -->
    <div class="mt-5 flex items-start gap-3">
      <span class="flex size-8 shrink-0 items-center justify-center rounded-full bg-white text-neutral-950">
        <UIcon name="i-lucide-sparkles" class="size-4" />
      </span>
      <div class="min-w-0 flex-1 rounded-2xl rounded-ss-sm bg-white p-4 text-neutral-950 shadow-xl">
        <p class="flex items-center gap-2 text-xs font-medium text-neutral-500">
          <span class="flex gap-0.5">
            <span class="size-1.5 rounded-full bg-violet-500 motion-safe:animate-pulse" />
            <span
              class="size-1.5 rounded-full bg-violet-500 motion-safe:animate-pulse [animation-delay:200ms]"
            />
            <span
              class="size-1.5 rounded-full bg-violet-500 motion-safe:animate-pulse [animation-delay:400ms]"
            />
          </span>
          {{ t('features.ai-assistant.drafted') }}
        </p>
        <ul class="mt-3 space-y-2">
          <li
            v-for="(field, i) in FIELDS"
            :key="i"
            class="flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2 motion-safe:animate-[feed_8s_ease-in-out_infinite] motion-safe:[animation-fill-mode:backwards]"
            :style="{ animationDelay: `${1.2 + i * 0.35}s` }"
          >
            <UIcon :name="field.icon" class="size-3.5 text-neutral-500" />
            <span class="h-1.5 rounded-full bg-neutral-300" :class="field.width" />
            <span class="ms-auto h-4 w-16 rounded border border-neutral-200" />
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

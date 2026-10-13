<script setup lang="ts">
// The API service, animated: a request is written, sent with its headers, and the 201 answer comes back while
// the calls counter moves on. Sample values only (no real keys or hosts, docs/SECURITY.md).
const { t, locale } = useI18n()
const root = useTemplateRef<HTMLElement>('root')

const ENDPOINTS = [
  { method: 'GET', path: '/responses', tone: 'text-emerald-600 dark:text-emerald-400 bg-emerald-500/10' },
  { method: 'POST', path: '/responses', tone: 'text-violet-600 dark:text-violet-300 bg-violet-500/10' },
  { method: 'PUT', path: '/responses/:id', tone: 'text-amber-600 dark:text-amber-300 bg-amber-500/10' },
  { method: 'DELETE', path: '/responses/:id', tone: 'text-red-600 dark:text-red-400 bg-red-500/10' },
]
const { step } = useDemoLoop(root, 3, 1400, 2)
const calls = computed(() => new Intl.NumberFormat(locale.value).format(4809 + step.value))
</script>

<template>
  <div ref="root">
    <DemoWindow :title="t('demo.apiService')" icon="i-lucide-braces">
      <template #actions>
        <span class="text-[10px] text-muted">
          {{ t('demo.callsToday') }}
          <span class="font-semibold text-highlighted tabular-nums">{{ calls }}</span>
        </span>
      </template>

      <div class="grid grid-cols-[9.5rem_minmax(0,1fr)] gap-3">
        <div>
          <p class="px-1 pb-1.5 text-[10px] font-semibold tracking-wide text-muted uppercase">
            {{ t('demo.endpoints') }}
          </p>
          <ul class="space-y-1">
            <li
              v-for="(item, i) in ENDPOINTS"
              :key="item.method"
              class="flex items-center gap-1.5 rounded-lg px-1.5 py-1.5 transition-colors"
              :class="i === 1 ? 'bg-elevated ring-1 ring-default' : ''"
            >
              <span
                class="w-11 shrink-0 rounded px-1 py-0.5 text-center font-mono text-[8px] font-bold"
                :class="item.tone"
                >{{ item.method }}</span
              >
              <span class="truncate font-mono text-[10px] text-toned">{{ item.path }}</span>
            </li>
          </ul>
        </div>

        <div class="min-w-0 space-y-2 font-mono text-[10px]" dir="ltr">
          <!-- The request -->
          <div class="rounded-xl bg-neutral-950 p-3 text-white/85 ring-1 ring-white/10">
            <p class="mb-1.5 font-sans text-[10px] font-semibold text-white/60">{{ t('demo.request') }}</p>
            <p class="flex">
              <span class="text-violet-300">POST</span>&nbsp;
              <span
                class="inline-block overflow-hidden whitespace-nowrap"
                :class="step >= 1 ? '' : 'motion-safe:animate-type'"
                >/v1/job-application/responses</span
              >
            </p>
            <p v-if="step >= 1" class="mt-1 text-white/50 motion-safe:animate-pop">
              Authorization: Bearer live_••••••••
            </p>
            <p v-if="step >= 1" class="text-white/50 motion-safe:animate-pop">Formalie-Key: 7f3a9c••••</p>
          </div>

          <!-- The answer -->
          <div class="min-h-[6.5rem] rounded-xl p-3 ring-1 ring-default">
            <p class="mb-1.5 flex items-center gap-2 font-sans text-[10px] font-semibold text-muted">
              {{ t('demo.response') }}
              <span
                v-if="step >= 2"
                class="rounded-full bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[9px] text-emerald-700 motion-safe:animate-pop dark:text-emerald-300"
                >201 · 84 ms</span
              >
              <span v-else class="flex gap-0.5">
                <span class="size-1 rounded-full bg-muted motion-safe:animate-pulse" />
                <span
                  class="size-1 rounded-full bg-muted motion-safe:animate-pulse [animation-delay:200ms]"
                />
                <span
                  class="size-1 rounded-full bg-muted motion-safe:animate-pulse [animation-delay:400ms]"
                />
              </span>
            </p>
            <div v-if="step >= 2" class="space-y-0.5 text-toned motion-safe:animate-pop">
              <p>{</p>
              <p class="ps-3">
                <span class="text-violet-600 dark:text-violet-300">"id"</span>: "rsp_8Hq2"<span
                  v-if="step >= 3"
                  >,</span
                >
              </p>
              <p v-if="step >= 3" class="ps-3 motion-safe:animate-pop">
                <span class="text-violet-600 dark:text-violet-300">"status"</span>: "new"
              </p>
              <p>}</p>
            </div>
          </div>
        </div>
      </div>
    </DemoWindow>
  </div>
</template>

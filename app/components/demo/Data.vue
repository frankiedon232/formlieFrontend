<script setup lang="ts">
// Data sources, animated: healthy connections pulse, and each answer is written to the customer's database as it
// arrives (a live log), while the traffic bars move on.
const { t } = useI18n()
const root = useTemplateRef<HTMLElement>('root')

// Sample connections (example.net hosts, as on the real screen).
const CONNECTIONS = [
  { name: 'Website leads', engine: 'MySQL', icon: 'i-simple-icons-mysql', ms: 12 },
  { name: 'Supplier records', engine: 'PostgreSQL', icon: 'i-simple-icons-postgresql', ms: 9 },
  { name: 'People records', engine: 'SQL Server', icon: 'i-simple-icons-microsoftsqlserver', ms: 15 },
]
const TABLES = ['fm_responses', 'fm_answers', 'fm_files']

const { step } = useDemoLoop(root, 6, 1200, 1)
const writes = computed(() =>
  Array.from({ length: Math.min(step.value + 1, 4) }, (_, i) => {
    const n = step.value - i
    return {
      id: 1250 + n,
      table: TABLES[n % TABLES.length]!,
      engine: CONNECTIONS[n % CONNECTIONS.length]!,
      ms: 8 + ((n * 7) % 9),
    }
  }),
)
const bars = computed(() => Array.from({ length: 14 }, (_, i) => 25 + (((i + step.value) * 37) % 70)))
</script>

<template>
  <div ref="root">
    <DemoWindow :title="t('demo.dataSources')" icon="i-lucide-database">
      <ul class="space-y-2">
        <li
          v-for="(item, i) in CONNECTIONS"
          :key="item.name"
          class="flex items-center gap-3 rounded-xl px-3 py-2 ring-1 ring-default"
        >
          <span class="flex size-8 items-center justify-center rounded-lg bg-elevated">
            <UIcon :name="item.icon" class="size-4 text-highlighted" />
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-[11px] font-semibold text-highlighted">{{ item.name }}</span>
            <span class="block truncate text-[10px] text-muted">{{ item.engine }}</span>
          </span>
          <span class="hidden text-[10px] text-muted tabular-nums sm:block">{{ item.ms }} ms</span>
          <span
            class="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[9px] font-medium text-emerald-700 dark:text-emerald-300"
          >
            <span class="relative flex size-1.5">
              <span
                class="absolute inline-flex size-full rounded-full bg-emerald-500 motion-safe:animate-ping-soft"
                :style="{ animationDelay: `${i * 0.6}s` }"
              />
              <span class="relative inline-flex size-1.5 rounded-full bg-emerald-500" />
            </span>
            {{ t('demo.connected') }}
          </span>
        </li>
      </ul>

      <div class="mt-3 grid grid-cols-[minmax(0,1fr)_7rem] gap-3">
        <div class="rounded-xl bg-neutral-950 p-3 font-mono text-[10px] text-white/80 ring-1 ring-white/10">
          <p class="mb-2 flex items-center gap-1.5 font-sans text-[10px] font-semibold text-white">
            <span class="size-1.5 rounded-full bg-emerald-400" />{{ t('demo.liveWrites') }}
          </p>
          <ul class="space-y-1">
            <li
              v-for="write in writes"
              :key="write.id"
              class="flex items-center gap-2 truncate motion-safe:animate-pop"
            >
              <UIcon name="i-lucide-check" class="size-3 shrink-0 text-emerald-400" />
              <span class="text-violet-300">INSERT</span>
              <span class="truncate">{{ write.table }} #{{ write.id }}</span>
              <span class="ms-auto shrink-0 text-white/50">{{ write.ms }} ms</span>
            </li>
          </ul>
        </div>
        <div class="flex flex-col rounded-xl p-3 ring-1 ring-default">
          <p class="text-[10px] text-muted">{{ t('demo.responseTime') }}</p>
          <p class="text-lg font-semibold text-highlighted tabular-nums">12 ms</p>
          <div class="mt-auto flex h-10 items-end gap-0.5">
            <span
              v-for="(h, i) in bars"
              :key="i"
              class="w-full rounded-sm bg-inverted/70 transition-[height] duration-700"
              :style="{ height: `${h}%` }"
            />
          </div>
        </div>
      </div>
    </DemoWindow>
  </div>
</template>

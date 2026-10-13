<script setup lang="ts">
// Responses, animated: new answers arrive at the top as "New", earlier ones are approved, the counter ticks.
const { t, locale } = useI18n()
const root = useTemplateRef<HTMLElement>('root')

// Sample respondents (English names, example.com addresses; docs/SECURITY.md: sample data only).
const PEOPLE = [
  { name: 'Emma Clarke', initials: 'EC' },
  { name: 'James Walker', initials: 'JW' },
  { name: 'Olivia Bennett', initials: 'OB' },
  { name: 'Henry Cooper', initials: 'HC' },
  { name: 'Lucy Morgan', initials: 'LM' },
  { name: 'Jack Ellis', initials: 'JE' },
]
const { step } = useDemoLoop(root, 4, 1500, 2)

// The newest `step + 2` people, newest first; the newest is New, the next one Reviewed, older ones Approved.
const rows = computed(() =>
  PEOPLE.slice(0, step.value + 2)
    .reverse()
    .slice(0, 4)
    .map((person, i) => ({
      ...person,
      email: `${person.name.split(' ')[0]!.toLowerCase()}@example.com`,
      status: i === 0 ? 'new' : i === 1 ? 'reviewed' : 'approved',
      when: i === 0 ? t('demo.justNow') : t('demo.minutesAgo', { n: i * 3 }),
    })),
)
const total = computed(() => new Intl.NumberFormat(locale.value).format(1252 + step.value + 2))
const BADGE: Record<string, string> = {
  new: 'bg-elevated text-toned ring-default',
  reviewed: 'bg-amber-500/10 text-amber-700 ring-amber-500/25 dark:text-amber-300',
  approved: 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/25 dark:text-emerald-300',
}
const BARS = [
  { key: 'new', color: 'bg-inverted', share: 53 },
  { key: 'reviewed', color: 'bg-amber-400', share: 27 },
  { key: 'approved', color: 'bg-emerald-500', share: 20 },
]
</script>

<template>
  <div ref="root">
    <DemoWindow :title="t('demo.responses')" icon="i-lucide-inbox">
      <div class="grid grid-cols-2 gap-3">
        <div class="rounded-xl p-3 ring-1 ring-default">
          <p class="text-[10px] text-muted">{{ t('demo.total') }}</p>
          <p
            :key="total"
            class="mt-1 text-2xl font-semibold tracking-tight text-highlighted tabular-nums motion-safe:animate-pop"
          >
            {{ total }}
          </p>
          <div class="mt-2 flex h-8 items-end gap-0.5">
            <span
              v-for="(h, i) in [30, 45, 38, 60, 52, 75, 68, 90]"
              :key="i"
              class="w-full rounded-sm bg-inverted/80"
              :style="{ height: `${h}%` }"
            />
          </div>
        </div>
        <div class="rounded-xl p-3 ring-1 ring-default">
          <p class="text-[10px] text-muted">{{ t('demo.status') }}</p>
          <div class="mt-2 flex h-2 overflow-hidden rounded-full">
            <span v-for="bar in BARS" :key="bar.key" :class="bar.color" :style="{ width: `${bar.share}%` }" />
          </div>
          <ul class="mt-2 space-y-1">
            <li v-for="bar in BARS" :key="bar.key" class="flex items-center gap-1.5 text-[10px] text-toned">
              <span class="size-2 rounded-full" :class="bar.color" />
              <span class="flex-1">{{ t(`demo.statuses.${bar.key}`) }}</span>
              <span class="tabular-nums">{{ bar.share }}%</span>
            </li>
          </ul>
        </div>
      </div>

      <div class="mt-3 overflow-hidden rounded-xl ring-1 ring-default">
        <div
          class="grid grid-cols-[minmax(0,1fr)_5rem_5.5rem] gap-2 border-b border-default bg-elevated/40 px-3 py-2 text-[10px] font-medium text-muted"
        >
          <span>{{ t('demo.respondent') }}</span>
          <span>{{ t('demo.submitted') }}</span>
          <span>{{ t('demo.status') }}</span>
        </div>
        <ul class="divide-y divide-default">
          <li
            v-for="row in rows"
            :key="row.name"
            class="grid grid-cols-[minmax(0,1fr)_5rem_5.5rem] items-center gap-2 px-3 py-2 motion-safe:animate-pop"
          >
            <span class="flex min-w-0 items-center gap-2">
              <span
                class="flex size-6 shrink-0 items-center justify-center rounded-full bg-elevated text-[9px] font-semibold text-toned"
                >{{ row.initials }}</span
              >
              <span class="min-w-0">
                <span class="block truncate text-[11px] font-medium text-highlighted">{{ row.name }}</span>
                <span class="block truncate text-[9px] text-muted">{{ row.email }}</span>
              </span>
            </span>
            <span class="truncate text-[10px] text-muted">{{ row.when }}</span>
            <span
              class="w-fit rounded-full px-2 py-0.5 text-[9px] font-medium ring-1 transition-colors duration-500"
              :class="BADGE[row.status]"
            >
              {{ t(`demo.statuses.${row.status}`) }}
            </span>
          </li>
        </ul>
      </div>
    </DemoWindow>
  </div>
</template>

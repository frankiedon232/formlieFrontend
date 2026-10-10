<!--
  Dashboard → first steps (F21 M5): what a new workspace sees in place of empty charts. A short welcome and the
  steps that get it going (first form, a template, set-up, the team, a database, help), each only when the
  person's role allows it. Someone who can't create forms sees that nothing has been shared with them yet.
-->
<script setup lang="ts">
const { t } = useI18n()
const { can } = useCan()

const steps = computed(() =>
  [
    { key: 'form', icon: 'i-lucide-file-plus-2', to: '/forms/new', show: can('forms.create'), primary: true },
    { key: 'template', icon: 'i-lucide-layout-template', to: '/templates', show: can('forms.create') },
    { key: 'setup', icon: 'i-lucide-building-2', to: '/onboarding', show: can('settings.manage') },
    { key: 'team', icon: 'i-lucide-user-plus', to: '/people', show: can('people.manage') },
    {
      key: 'database',
      icon: 'i-lucide-database',
      to: '/data-sources/connections/new',
      show: can('data.create'),
    },
    { key: 'help', icon: 'i-lucide-life-buoy', to: '/help', show: true },
  ].filter(step => step.show),
)
</script>

<template>
  <AppEmpty
    v-if="!can('forms.create')"
    icon="i-lucide-folder-open"
    :title="t('dashboard.start.sharedTitle')"
    :description="t('dashboard.start.sharedDesc')"
    :actions="[
      {
        label: t('dashboard.start.steps.help.title'),
        icon: 'i-lucide-life-buoy',
        color: 'neutral',
        variant: 'outline',
        to: '/help',
      },
    ]"
  />
  <UCard v-else variant="outline" :ui="{ body: 'flex flex-col gap-5 p-4 sm:p-6' }">
    <div class="flex flex-col gap-1">
      <h2 class="text-lg font-semibold text-highlighted">{{ t('dashboard.start.title') }}</h2>
      <p class="text-sm text-muted">{{ t('dashboard.start.description') }}</p>
    </div>
    <ol class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <li v-for="(step, i) in steps" :key="step.key" class="min-w-0">
        <NuxtLink
          :to="step.to"
          class="flex h-full items-start gap-3 rounded-md border border-default p-4 transition hover:border-accented hover:shadow-sm focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
          :class="step.primary ? 'border-inverted' : ''"
        >
          <span
            class="flex size-9 shrink-0 items-center justify-center rounded-full border border-default"
            :class="step.primary ? 'bg-inverted text-inverted' : 'text-highlighted'"
          >
            <UIcon :name="step.icon" class="size-4" />
          </span>
          <span class="flex min-w-0 flex-1 flex-col gap-0.5">
            <span class="text-[11px] text-muted tabular-nums">{{
              t('dashboard.start.step', { n: i + 1 })
            }}</span>
            <span class="text-sm font-medium text-highlighted">{{
              t(`dashboard.start.steps.${step.key}.title`)
            }}</span>
            <span class="text-xs text-muted">{{ t(`dashboard.start.steps.${step.key}.desc`) }}</span>
          </span>
          <UIcon name="i-lucide-arrow-up-right" class="size-4 shrink-0 text-muted rtl:-scale-x-100" />
        </NuxtLink>
      </li>
    </ol>
  </UCard>
</template>

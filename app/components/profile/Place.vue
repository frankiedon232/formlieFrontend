<!-- My profile → In the workspace (F16 M5): role, departments, job titles and manager, set by admins on People. -->
<script setup lang="ts">
import type { MyProfile } from '#shared/types/profile'

const props = defineProps<{ profile: MyProfile }>()
const { t } = useI18n()
const { roleName } = useBuiltInNames()
const names = (items: { name: string }[]) => items.map(item => item.name).join(', ') || t('people.none')
const tiles = computed(() => [
  { key: 'role', icon: 'i-lucide-shield', label: t('people.col.role'), value: roleName(props.profile.role, props.profile.role_name) },
  { key: 'departments', icon: 'i-lucide-building-2', label: t('people.col.departments'), value: names(props.profile.departments) },
  { key: 'jobs', icon: 'i-lucide-briefcase', label: t('people.col.jobTitles'), value: names(props.profile.job_titles) },
  { key: 'manager', icon: 'i-lucide-user-round', label: t('people.col.manager'), value: props.profile.manager?.name ?? t('people.none') },
])
</script>

<template>
  <SettingsBlock :title="t('profile.place.title')" :description="t('profile.place.desc')" icon="i-lucide-building-2">
    <div class="grid gap-2 sm:grid-cols-2">
      <div v-for="tile in tiles" :key="tile.key" class="flex h-full min-w-0 items-center gap-2.5 rounded-lg border border-default p-2.5">
        <span class="flex size-8 shrink-0 items-center justify-center rounded-md bg-elevated"><UIcon :name="tile.icon" class="size-4 text-muted" /></span>
        <div class="flex min-w-0 flex-col">
          <span class="truncate text-[11px] text-muted">{{ tile.label }}</span>
          <span class="truncate text-sm font-semibold text-highlighted">{{ tile.value }}</span>
        </div>
      </div>
    </div>
  </SettingsBlock>
</template>

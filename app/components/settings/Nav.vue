<!--
  The Settings navigator (F14): a search, then the sections in their groups, the current one marked.
  Live sections are links; the ones still to come show "Soon" with their milestone and are not links,
  so the whole plan is visible without dead ends. Used in the menu column (sidebar takeover) on
  desktop and in a side panel elsewhere.
-->
<script setup lang="ts">
const emit = defineEmits<{ navigate: [] }>()
const { t } = useI18n()
const { groups, label, description, current } = useSettingsSections()
const q = ref('')
const match = (key: string) => {
  const needle = q.value.trim().toLowerCase()
  if (!needle) return true
  const item = groups.flatMap(group => group.items).find(entry => entry.key === key)!
  return `${label(item)} ${description(item)}`.toLowerCase().includes(needle)
}
const shown = computed(() => groups.map(group => ({ ...group, items: group.items.filter(item => match(item.key)) })).filter(group => group.items.length))
</script>

<template>
  <nav class="flex min-h-0 flex-1 flex-col" :aria-label="t('settings.title')">
    <div class="shrink-0 p-3 pb-2">
      <UInput v-model="q" icon="i-lucide-search" :placeholder="t('settings.search')" size="sm" class="w-full" :aria-label="t('settings.search')">
        <template v-if="q" #trailing>
          <UButton icon="i-lucide-x" color="neutral" variant="link" size="xs" :aria-label="t('common.clear')" @click="q = ''" />
        </template>
      </UInput>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
      <p v-if="!shown.length" class="px-2 py-6 text-center text-xs text-muted">{{ t('settings.noMatch') }}</p>
      <div v-for="group in shown" :key="group.key" class="flex flex-col gap-0.5 pt-3 first:pt-1">
        <span class="px-2 pb-1 text-[11px] font-medium tracking-wide text-muted uppercase">{{ t(`settings.group.${group.key}`) }}</span>
        <template v-for="item in group.items" :key="item.key">
          <NuxtLink
            v-if="item.to"
            :to="item.to"
            class="group flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
            :class="current?.key === item.key ? 'bg-elevated font-medium text-highlighted ring-1 ring-default' : 'text-default hover:bg-elevated/60 hover:text-highlighted'"
            :aria-current="current?.key === item.key ? 'page' : undefined"
            @click="emit('navigate')"
          >
            <UIcon :name="item.icon" class="size-4 shrink-0" :class="current?.key === item.key ? 'text-highlighted' : 'text-muted group-hover:text-highlighted'" />
            <span class="line-clamp-2 min-w-0 flex-1 leading-snug">{{ label(item) }}</span>
            <UIcon v-if="item.to.startsWith('/option-sets')" name="i-lucide-arrow-up-right" class="size-3.5 shrink-0 text-dimmed rtl:-scale-x-100" />
          </NuxtLink>
          <div v-else class="flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm text-muted" :aria-disabled="true">
            <UIcon :name="item.icon" class="size-4 shrink-0 text-dimmed" />
            <span class="line-clamp-2 min-w-0 flex-1 leading-snug">{{ label(item) }}</span>
            <UBadge :label="t('settings.soon')" color="neutral" variant="soft" size="xs" class="shrink-0 rounded-md" />
          </div>
        </template>
      </div>
    </div>
  </nav>
</template>

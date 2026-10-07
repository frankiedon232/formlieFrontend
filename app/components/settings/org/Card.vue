<!--
  An organisation entry as a card (F14 M2; locked card format, rule 21): an "updated" pill, its state
  and ⋯ on top; the name (red flag when nobody is in it) and its description or code; people, forms,
  code and created in two columns; a divider, then its share of the workspace's people as a slim bar;
  the first people's initials and the counts at the bottom.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { OrgItem } from '#shared/types/org'

const props = defineProps<{ item: OrgItem; people: number; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number, percent, date } = useFormat()
const empty = computed(() => props.item.status === 'active' && !props.item.members.length)
const share = computed(() => (props.people ? props.item.members.length / props.people : 0))
const facts = computed(() => [
  { key: 'people', label: t('settings.org.col.people'), value: t('settings.org.peopleCount', { n: number(props.item.members.length) }, props.item.members.length) },
  { key: 'forms', label: t('settings.org.col.forms'), value: t('settings.org.formsCount', { n: number(props.item.forms_count) }, props.item.forms_count) },
  { key: 'code', label: t('settings.org.col.code'), value: props.item.code ?? '–' },
  { key: 'created', label: t('settings.org.col.created'), value: date(props.item.created_at) },
])
const initials = (name: string) => name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()
</script>

<template>
  <article class="group relative flex h-full flex-col rounded-lg border border-default bg-default p-4 transition-all hover:-translate-y-0.5 hover:border-accented hover:shadow-md focus-within:shadow-md" :class="busy ? 'pointer-events-none opacity-60' : ''" :aria-busy="busy || undefined">
    <div class="flex items-center justify-between gap-2">
      <span class="inline-flex min-w-0 items-center gap-1.5 rounded-md border border-default px-2 py-0.5 text-xs font-medium text-toned">
        <UIcon :name="busy ? 'i-lucide-loader-circle' : 'i-lucide-clock'" class="size-3.5 shrink-0 text-muted" :class="busy ? 'animate-spin' : ''" />
        <span class="truncate">{{ t('settings.org.updated', { when: relative(item.updated_at) }) }}</span>
      </span>
      <div class="flex shrink-0 items-center gap-1.5">
        <SettingsOrgState :item="item" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" square :aria-label="t('dataView.actions')" />
        </UDropdownMenu>
      </div>
    </div>

    <div class="mt-3 flex min-w-0 flex-col">
      <div class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="empty" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('settings.org.nobody')" />
        <span class="truncate font-semibold text-highlighted" :class="item.status === 'archived' ? 'line-through decoration-1' : ''">{{ item.name }}</span>
      </div>
      <span class="truncate text-sm text-muted">{{ item.description || item.code || t('settings.org.noDescription') }}</span>
    </div>

    <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
      <div v-for="fact in facts" :key="fact.key" class="flex min-w-0 items-baseline justify-between gap-2">
        <dt class="shrink-0 text-muted">{{ fact.label }}</dt>
        <dd class="truncate font-medium text-highlighted tabular-nums">{{ fact.value }}</dd>
      </div>
    </dl>

    <div class="mt-auto flex flex-col gap-3 pt-3">
      <USeparator />
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="text-muted">{{ t('settings.org.shareOfPeople') }}</span>
          <span class="font-medium text-highlighted tabular-nums">{{ percent(share) }}</span>
        </div>
        <UProgress :model-value="share * 100" color="neutral" size="xs" />
      </div>
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center">
          <span v-for="(person, i) in item.members.slice(0, 3)" :key="person.id" class="flex size-6 items-center justify-center rounded-full border-2 border-(--ui-bg) bg-elevated text-[10px] font-semibold text-highlighted" :class="i ? '-ms-1.5' : ''" :title="person.name">{{ initials(person.name) }}</span>
          <span v-if="item.members.length > 3" class="ms-1.5 text-xs text-muted tabular-nums">+{{ item.members.length - 3 }}</span>
          <span v-if="!item.members.length" class="text-xs text-muted">{{ t('settings.org.nobody') }}</span>
        </div>
        <span class="inline-flex items-center gap-1 text-xs text-muted tabular-nums"><UIcon name="i-lucide-file-text" class="size-3.5" />{{ number(item.forms_count) }}</span>
      </div>
    </div>
  </article>
</template>

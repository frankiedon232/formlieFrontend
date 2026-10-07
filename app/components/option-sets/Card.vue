<!--
  List Option, grid card (locked card format, rule 21): pill with when it changed, state and ⋯ on top;
  name (red flag = retired options to look at) and description; options and forms; the first options
  as chips; languages fully translated; who made it. The whole card opens the list.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { OptionListRow } from '#shared/types/forms'

const props = defineProps<{ item: OptionListRow; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number } = useFormat()
const preview = computed(() => props.item.options.filter(option => option.active !== false).slice(0, 4))
const more = computed(() => props.item.items_count - preview.value.length)
</script>

<template>
  <div class="flex h-full flex-col gap-3 rounded-xl border border-default bg-default p-4 transition hover:border-accented hover:shadow-sm" :class="busy ? 'pointer-events-none opacity-60' : ''">
    <div class="flex items-center justify-between gap-2">
      <span class="flex min-w-0 items-center gap-1.5 rounded-full border border-default px-2 py-0.5 text-[11px] text-muted"><UIcon name="i-lucide-clock" class="size-3" />{{ relative(item.updated_at) }}</span>
      <div class="flex items-center gap-1">
        <UBadge :label="item.forms_count ? t('optionSets.state.in_use') : t('optionSets.state.unused')" :color="item.forms_count ? 'success' : 'warning'" variant="subtle" size="sm" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" :loading="busy" :aria-label="t('dataView.actions')" @click.stop />
        </UDropdownMenu>
      </div>
    </div>
    <div class="flex min-w-0 flex-col gap-0.5">
      <span class="flex min-w-0 items-center gap-1.5">
        <UIcon v-if="item.retired_count" name="i-lucide-flag" class="size-3.5 shrink-0 text-error" :aria-label="t('optionSets.hasRetired')" />
        <span class="truncate font-semibold text-highlighted">{{ item.name }}</span>
      </span>
      <span class="line-clamp-1 text-xs text-muted">{{ item.description || t('optionSets.noDescription') }}</span>
    </div>
    <dl class="grid grid-cols-2 gap-2 text-xs">
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('optionSets.col.items') }}</dt><dd class="font-medium text-highlighted tabular-nums">{{ t('optionSets.itemsCount', { n: number(item.items_count) }, item.items_count) }}</dd></div>
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('optionSets.col.forms') }}</dt><dd class="font-medium text-highlighted tabular-nums">{{ t('optionSets.formsCount', { n: number(item.forms_count) }, item.forms_count) }}</dd></div>
    </dl>
    <div class="flex flex-wrap gap-1">
      <UBadge v-for="option in preview" :key="option.value" :label="option.label" color="neutral" variant="outline" size="sm" class="max-w-36 truncate" />
      <UBadge v-if="more > 0" :label="`+${number(more)}`" color="neutral" variant="soft" size="sm" />
    </div>
    <div class="mt-auto flex items-center justify-between gap-2 border-t border-default pt-3 text-[11px] text-muted">
      <span class="flex min-w-0 items-center gap-1.5 truncate"><UIcon name="i-lucide-user-round" class="size-3.5 shrink-0" />{{ item.created_by.name }}</span>
      <span class="flex shrink-0 items-center gap-1"><UIcon name="i-lucide-languages" class="size-3.5" />{{ item.languages.length ? item.languages.map(code => code.toUpperCase()).join(' · ') : t('optionSets.oneLanguage') }}</span>
    </div>
  </div>
</template>

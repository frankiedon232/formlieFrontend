<!--
  Settings → Organisations, grid card (locked card format, rule 21): pill with when it changed, state
  and ⋯ on top; logo or initials with name and website; forms and responses; share of the workspace's
  forms as a slim bar; short name and "main" at the bottom. The whole card opens it.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { Organisation } from '#shared/types/organisations'

const props = defineProps<{ item: Organisation; totalForms: number; actions: DropdownMenuItem[][]; busy?: boolean }>()
const { t } = useI18n()
const { relative, number, percent } = useFormat()
const share = computed(() => (props.totalForms ? props.item.forms_count / props.totalForms : 0))
const initials = computed(() => organisationInitials(props.item))
</script>

<template>
  <div class="flex h-full flex-col gap-3 rounded-xl border border-default bg-default p-4 transition hover:border-accented hover:shadow-sm" :class="busy ? 'pointer-events-none opacity-60' : ''">
    <div class="flex items-center justify-between gap-2">
      <span class="flex min-w-0 items-center gap-1.5 rounded-full border border-default px-2 py-0.5 text-[11px] text-muted"><UIcon name="i-lucide-clock" class="size-3" />{{ relative(item.updated_at) }}</span>
      <div class="flex items-center gap-1">
        <UBadge :label="item.status === 'active' ? t('organisations.active') : t('organisations.archived')" :color="item.status === 'active' ? 'success' : 'neutral'" variant="subtle" size="sm" />
        <UDropdownMenu :items="actions" :content="{ align: 'end' }">
          <UButton icon="i-lucide-ellipsis" color="neutral" variant="outline" size="xs" :loading="busy" :aria-label="t('dataView.actions')" @click.stop />
        </UDropdownMenu>
      </div>
    </div>
    <div class="flex items-center gap-3">
      <span class="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-default bg-elevated text-sm font-semibold text-highlighted">
        <img v-if="item.logo_url" :src="item.logo_url" alt="" class="max-h-full max-w-full object-contain">
        <span v-else>{{ initials }}</span>
      </span>
      <span class="flex min-w-0 flex-col">
        <span class="truncate font-semibold text-highlighted">{{ item.name }}</span>
        <span class="truncate text-xs text-muted">{{ item.website ?? t('organisations.noWebsite') }}</span>
      </span>
    </div>
    <dl class="grid grid-cols-2 gap-2 text-xs">
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('organisations.forms') }}</dt><dd class="font-medium text-highlighted tabular-nums">{{ t('organisations.formsCount', { n: number(item.forms_count) }, item.forms_count) }}</dd></div>
      <div class="flex min-w-0 flex-col"><dt class="text-muted">{{ t('organisations.responses') }}</dt><dd class="font-medium text-highlighted tabular-nums">{{ number(item.responses_count) }}</dd></div>
    </dl>
    <div class="mt-auto flex flex-col gap-1.5 border-t border-default pt-3">
      <div class="flex items-center justify-between text-xs"><span class="text-muted">{{ t('organisations.shareOfForms') }}</span><span class="font-medium text-highlighted tabular-nums">{{ percent(share) }}</span></div>
      <div class="h-1 overflow-hidden rounded-full bg-elevated"><div class="h-full rounded-full bg-inverted" :style="{ width: `${share * 100}%` }" /></div>
      <div class="flex items-center justify-between gap-2 pt-1 text-[11px] text-muted">
        <span class="truncate font-mono">{{ item.short_name ?? '' }}</span>
        <UBadge v-if="item.main" :label="t('organisations.main')" color="neutral" variant="outline" size="xs" icon="i-lucide-star" />
      </div>
    </div>
  </div>
</template>

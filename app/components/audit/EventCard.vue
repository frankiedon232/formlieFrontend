<!-- Grid card for one audit event (same card language as the forms grid). The whole card opens the details. -->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { AuditEvent } from '#shared/types/audit'

const props = defineProps<{ event: AuditEvent; actions: DropdownMenuItem[][] }>()
const emit = defineEmits<{ open: [event: AuditEvent] }>()
const { t } = useI18n()
const { dateTime, relative } = useFormat()
const format = useAuditFormat()
</script>

<template>
  <UCard :ui="{ body: 'flex flex-col gap-3 p-4 sm:p-4' }" class="h-full">
    <div class="flex items-center justify-between gap-2">
      <UBadge
        :label="format.outcomeLabel(props.event.outcome)"
        :color="format.outcomeColor(props.event.outcome)"
        variant="subtle"
        size="sm"
        class="rounded-md"
      />
      <UDropdownMenu :items="props.actions" :content="{ align: 'end' }">
        <UButton
          icon="i-lucide-ellipsis"
          color="neutral"
          variant="ghost"
          size="xs"
          square
          :aria-label="t('dataView.actions')"
        />
      </UDropdownMenu>
    </div>

    <UButton
      color="neutral"
      variant="ghost"
      class="-mx-2 min-w-0 items-start gap-3 text-start"
      @click="emit('open', props.event)"
    >
      <span
        class="flex size-9 shrink-0 items-center justify-center rounded-md border border-default bg-elevated/50"
      >
        <UIcon :name="format.actionIcon(props.event.action)" class="size-4 text-highlighted" />
      </span>
      <span class="min-w-0">
        <span class="block truncate font-semibold text-highlighted">{{
          format.actionLabel(props.event.action)
        }}</span>
        <span class="block truncate text-sm text-muted">
          {{ props.event.resource?.name ?? format.areaLabel(props.event.area) }}
        </span>
      </span>
    </UButton>

    <div class="flex items-center gap-1.5 text-sm text-muted">
      <UIcon
        v-if="props.event.location.country"
        :name="format.countryFlag(props.event.location.country)"
        class="size-4 shrink-0"
      />
      <UIcon v-else name="i-lucide-map-pin-off" class="size-4 shrink-0" />
      <span class="truncate">{{ format.place(props.event) }}</span>
    </div>

    <div class="mt-auto flex items-center justify-between gap-2 border-t border-default pt-3 text-sm">
      <UUser
        :name="props.event.actor.name"
        :avatar="{ alt: props.event.actor.name, icon: props.event.actor.id ? undefined : 'i-lucide-user-x' }"
        size="xs"
        :ui="{ name: 'truncate max-w-36' }"
      />
      <UTooltip :text="dateTime(props.event.occurred_at)">
        <span class="whitespace-nowrap text-muted">{{ relative(props.event.occurred_at) }}</span>
      </UTooltip>
    </div>
  </UCard>
</template>

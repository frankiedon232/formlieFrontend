<!--
  One field on the canvas: the real field (renderer, non-interactive) inside a selectable frame.
  Hover → hairline border; selected → dark outline (monochrome, docs/design). Type pill and the
  small outline icon buttons (drag · duplicate · delete · ⋯) show on hover / selection / focus.
  Click selects, Ctrl/⌘ toggles, Shift selects a range; Enter / Space select from the keyboard.
-->
<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { FormField } from '#shared/utils/forms/build'
import { FIELD_WIDTHS } from '#shared/utils/forms/fields'

const props = defineProps<{ field: FormField; selected: boolean; issue?: string }>()
const emit = defineEmits<{ remove: [] }>()
const { t } = useI18n()
const builder = useBuilder()

function onSelect(event: MouseEvent | KeyboardEvent) {
  builder.select(
    props.field.id,
    event.shiftKey ? 'range' : event.metaKey || event.ctrlKey ? 'toggle' : 'only',
  )
}

const WIDTH_LABEL: Record<number, string> = { 12: '1/1', 6: '1/2', 4: '1/3', 8: '2/3', 3: '1/4', 9: '3/4' }
const menu = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t('builder.actions.moveUp'),
      icon: 'i-lucide-arrow-up',
      kbds: ['alt', 'arrowup'],
      onSelect: () => builder.move(props.field.id, -1),
    },
    {
      label: t('builder.actions.moveDown'),
      icon: 'i-lucide-arrow-down',
      kbds: ['alt', 'arrowdown'],
      onSelect: () => builder.move(props.field.id, 1),
    },
    {
      label: t('builder.actions.moveToPage'),
      icon: 'i-lucide-file-symlink',
      disabled: builder.pages.value.length < 2,
      children: builder.pages.value.map((p, i) => ({
        label: p.title || t('builder.page.default', { n: i + 1 }),
        disabled: p.id === builder.findField(props.field.id)?.page.id,
        onSelect: () => builder.moveToPage([props.field.id], p.id),
      })),
    },
  ],
  [
    {
      label: t('builder.actions.width'),
      icon: 'i-lucide-columns-3',
      children: FIELD_WIDTHS.map(width => ({
        label: `${WIDTH_LABEL[width]} · ${t(`builder.width.${width}`)}`,
        type: 'checkbox' as const,
        checked: (props.field.width ?? 12) === width,
        onSelect: () => builder.setWidth([props.field.id], width),
      })),
    },
    {
      label: t('builder.actions.duplicate'),
      icon: 'i-lucide-copy',
      kbds: ['meta', 'd'],
      onSelect: () => builder.duplicate([props.field.id]),
    },
  ],
  [
    {
      label: t('builder.actions.delete'),
      icon: 'i-lucide-trash-2',
      color: 'error' as const,
      kbds: ['delete'],
      onSelect: () => emit('remove'),
    },
  ],
])
</script>

<template>
  <div
    class="group/field relative rounded-lg border p-3 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-(--ui-border-inverted)"
    :class="
      selected
        ? 'border-(--ui-border-inverted) bg-elevated/30 ring-1 ring-(--ui-border-inverted)'
        : issue
          ? 'border-warning/60 hover:border-warning'
          : 'border-transparent hover:border-default'
    "
    role="button"
    tabindex="0"
    :aria-pressed="selected"
    :aria-label="
      t('builder.fieldAria', {
        label: field.label || t(`builder.field.${field.type}`),
        type: t(`builder.field.${field.type}`),
      })
    "
    :data-field-id="field.id"
    @click.stop="onSelect"
    @keydown.enter.self.prevent="onSelect"
    @keydown.space.self.prevent="onSelect"
  >
    <div
      class="absolute -top-3 start-3 z-10 flex items-center gap-1 transition-opacity"
      :class="
        selected
          ? 'opacity-100'
          : 'opacity-0 group-hover/field:opacity-100 group-focus-within/field:opacity-100'
      "
    >
      <UBadge
        :icon="fieldIcon(field.type)"
        :label="t(`builder.field.${field.type}`)"
        color="neutral"
        variant="outline"
        size="sm"
        class="rounded-md bg-default"
      />
      <UBadge
        v-if="issue"
        :label="issue"
        icon="i-lucide-triangle-alert"
        color="warning"
        variant="subtle"
        size="sm"
        class="rounded-md"
      />
    </div>

    <div
      class="absolute -top-3.5 end-2 z-10 flex items-center gap-1 transition-opacity"
      :class="
        selected
          ? 'opacity-100'
          : 'opacity-0 group-hover/field:opacity-100 group-focus-within/field:opacity-100'
      "
      @click.stop
    >
      <UTooltip :text="t('builder.actions.drag')">
        <UButton
          icon="i-lucide-grip-vertical"
          color="neutral"
          variant="outline"
          size="xs"
          square
          class="cursor-grab bg-default active:cursor-grabbing"
          data-drag-handle
          :aria-label="t('builder.actions.drag')"
        />
      </UTooltip>
      <UButton
        icon="i-lucide-copy"
        color="neutral"
        variant="outline"
        size="xs"
        square
        class="bg-default"
        :aria-label="t('builder.actions.duplicate')"
        @click="builder.duplicate([field.id])"
      />
      <UButton
        icon="i-lucide-trash-2"
        color="neutral"
        variant="outline"
        size="xs"
        square
        class="bg-default"
        :aria-label="t('builder.actions.delete')"
        @click="emit('remove')"
      />
      <UDropdownMenu :items="menu" :content="{ align: 'end' }">
        <UButton
          icon="i-lucide-ellipsis"
          color="neutral"
          variant="outline"
          size="xs"
          square
          class="bg-default"
          :aria-label="t('builder.actions.more')"
        />
      </UDropdownMenu>
    </div>

    <!-- The real field, as respondents see it; not interactive inside the builder. -->
    <div inert class="pointer-events-none select-none">
      <FormsRendererField :field="field" mode="builder" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

// Light, dark or system (CLAUDE.md rule 12). The choice is the only thing kept besides the language.
const { t } = useI18n()
const colorMode = useColorMode()

const modes = [
  { value: 'light', icon: 'i-lucide-sun' },
  { value: 'dark', icon: 'i-lucide-moon' },
  { value: 'system', icon: 'i-lucide-monitor' },
] as const

const icon = computed(
  () => modes.find(mode => mode.value === colorMode.preference)?.icon ?? 'i-lucide-monitor',
)

const items = computed<DropdownMenuItem[]>(() =>
  modes.map(mode => ({
    label: t(`theme.${mode.value}`),
    icon: mode.icon,
    type: 'checkbox' as const,
    checked: colorMode.preference === mode.value,
    onSelect: () => {
      colorMode.preference = mode.value
    },
  })),
)
</script>

<template>
  <UDropdownMenu :items="items" :content="{ align: 'end' }">
    <UButton color="neutral" variant="ghost" :aria-label="t('theme.label')">
      <!-- The saved choice is only known in the browser, so the server renders the neutral icon. -->
      <ClientOnly>
        <UIcon :name="icon" class="size-5" />
        <template #fallback>
          <UIcon name="i-lucide-monitor" class="size-5" />
        </template>
      </ClientOnly>
    </UButton>
  </UDropdownMenu>
</template>

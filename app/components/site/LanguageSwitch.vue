<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'

// Language switch with flags (the app's list). Each entry opens the same page in that language.
const props = withDefaults(defineProps<{ showName?: boolean }>(), { showName: false })

const { t, locale, setLocale } = useI18n()

const current = computed(() => SITE_LOCALES.find(item => item.code === locale.value) ?? SITE_LOCALES[0]!)

const items = computed<DropdownMenuItem[]>(() =>
  SITE_LOCALES.map(item => ({
    label: item.name,
    icon: item.flag,
    // setLocale also stores the choice, so the remembered language never sends people back.
    onSelect: () => setLocale(item.code as typeof locale.value),
    type: 'checkbox' as const,
    checked: item.code === locale.value,
  })),
)
</script>

<template>
  <UDropdownMenu :items="items" :content="{ align: 'end' }" :ui="{ content: 'max-h-96 w-56' }">
    <UButton
      :icon="current.flag"
      :label="props.showName ? current.name : undefined"
      :aria-label="`${t('language.label')}: ${current.name}`"
      color="neutral"
      variant="ghost"
    />
  </UDropdownMenu>
</template>

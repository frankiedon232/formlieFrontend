<!--
  Language switcher on a form that speaks several languages (F10 M4, decision 99): flag and the
  language's own name. Shown only when there is a choice; answers stay when switching. `bar`: the
  page frame's top bar, beside "Visit website" (same round outline, takes the bar's text colour;
  narrow screens show the flag only).
-->
<script setup lang="ts">
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ languages: string[]; bar?: boolean }>()
const model = defineModel<string>({ required: true })
const { t } = useI18n()

const items = computed(() =>
  props.languages.map(code => {
    const locale = APP_LOCALES.find(item => item.code === code)
    return { value: code, label: locale?.name ?? code, icon: locale?.flag }
  }),
)
const flag = computed(() => items.value.find(item => item.value === model.value)?.icon)
</script>

<template>
  <USelectMenu
    v-if="languages.length > 1"
    v-model="model"
    :items="items"
    value-key="value"
    :search-input="languages.length > 6 ? { placeholder: t('common.search') } : false"
    :icon="flag"
    color="neutral"
    variant="outline"
    size="sm"
    :class="bar ? 'shrink-0 rounded-full border-current/25 bg-transparent text-current ring-current/25 hover:bg-current/10' : 'w-40'"
    :ui="bar ? { value: 'text-current @max-xl:sr-only', trailingIcon: 'text-current/70' } : undefined"
    :content="{ align: 'end' }"
    :aria-label="t('renderer.language')"
  />
</template>

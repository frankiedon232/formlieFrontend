<!--
  Language switcher on a form that speaks several languages (F10 M4, decision 99): flag and the
  language's own name. Shown only when there is a choice; answers stay when switching.
-->
<script setup lang="ts">
import { APP_LOCALES } from '#shared/utils/i18n/locales'

const props = defineProps<{ languages: string[] }>()
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
    class="w-40"
    :content="{ align: 'end' }"
    :aria-label="t('renderer.language')"
  />
</template>

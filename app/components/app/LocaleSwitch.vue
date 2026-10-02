<script setup lang="ts">
const { t } = useI18n()
const { locale, locales, current, changeLocale } = useAppLocale()
const items = computed(() => locales.map(item => ({ ...item, icon: item.flag })))

const loading = ref(false)

const selected = computed({
  get: () => locale.value,
  set: async (code: string) => {
    loading.value = true
    try {
      await changeLocale(code)
    } catch (error) {
      console.error('[locale]', error)
    } finally {
      loading.value = false
    }
  },
})
</script>

<template>
  <USelectMenu
    v-model="selected"
    :items="items"
    value-key="code"
    label-key="name"
    description-key="englishName"
    :filter-fields="['name', 'englishName', 'code']"
    :search-input="{ placeholder: t('common.search') }"
    :loading="loading"
    :aria-label="t('common.language')"
    :icon="current.flag"
    color="neutral"
    variant="ghost"
    :content="{ align: 'end' }"
    :ui="{ content: 'min-w-48' }"
  />
</template>

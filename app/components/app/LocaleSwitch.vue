<script setup lang="ts">
const { t } = useI18n()
const { locale, locales, changeLocale } = useAppLocale()

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
    :items="locales"
    value-key="code"
    label-key="name"
    description-key="englishName"
    :filter-fields="['name', 'englishName', 'code']"
    :search-input="{ placeholder: t('common.search') }"
    :loading="loading"
    :aria-label="t('common.language')"
    icon="i-lucide-languages"
    color="neutral"
    variant="ghost"
    :content="{ align: 'end' }"
    :ui="{ content: 'min-w-48' }"
  />
</template>

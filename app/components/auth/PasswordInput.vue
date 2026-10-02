<!-- Password field with show/hide toggle (keyboard reachable, announced). -->
<script setup lang="ts">
defineProps<{ autocomplete?: string; placeholder?: string }>()
const model = defineModel<string>({ default: '' })
const { t } = useI18n()
const visible = ref(false)
</script>

<template>
  <UInput
    v-model="model"
    :type="visible ? 'text' : 'password'"
    :autocomplete="autocomplete"
    :placeholder="placeholder"
    class="w-full"
    :ui="{ trailing: 'pe-1' }"
  >
    <template #trailing>
      <UButton
        :icon="visible ? 'i-lucide-eye-off' : 'i-lucide-eye'"
        color="neutral"
        variant="link"
        size="sm"
        :aria-label="visible ? t('auth.password.hide') : t('auth.password.show')"
        :aria-pressed="visible"
        @click="visible = !visible"
      />
    </template>
  </UInput>
</template>

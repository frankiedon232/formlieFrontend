<!-- Password field with show/hide toggle (keyboard reachable, announced). -->
<script setup lang="ts">
import type { InputProps } from '@nuxt/ui'

defineProps<{
  autocomplete?: string
  placeholder?: string
  size?: InputProps['size']
  icon?: string
}>()
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
    :size="size"
    :icon="icon"
    class="w-full"
    :ui="{ trailing: 'pe-1.5' }"
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

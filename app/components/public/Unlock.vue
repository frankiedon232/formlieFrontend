<!--
  Password screen for a protected public form (F10 M3). The password goes to the API
  (POST /public/forms/{key}/unlock, enveloped); the right one gives this browser an HttpOnly
  unlock cookie, then the form loads. Wrong passwords say so; too many tries slow down.
-->
<script setup lang="ts">
const props = defineProps<{ formKey: string }>()
const emit = defineEmits<{ unlocked: [] }>()
const { t } = useI18n()
const api = useApi()
const { handle } = useErrorHandler()

const password = ref('')
const show = ref(false)
const wrong = ref(false)
const { busy, run } = useBusy()
async function unlock() {
  if (!password.value) return
  wrong.value = false
  await run(async () => {
    try {
      await api.post(`/public/forms/${encodeURIComponent(props.formKey)}/unlock`, { password: password.value })
      emit('unlocked')
    } catch (error) {
      const failure = handle(error, { silent: true })
      if (failure.code === 'FRM-FORM-1017') wrong.value = true
      else handle(error)
    }
  })
}
</script>

<template>
  <form class="flex w-full flex-col gap-3 text-start" @submit.prevent="unlock">
    <UFormField :label="t('public.locked.password')" :error="wrong ? t('public.locked.wrong') : undefined">
      <UInput
        v-model="password"
        :type="show ? 'text' : 'password'"
        autocomplete="current-password"
        icon="i-lucide-key-round"
        class="w-full"
        autofocus
        :ui="{ trailing: 'pe-1' }"
        @update:model-value="wrong = false"
      >
        <template #trailing>
          <UButton
            :icon="show ? 'i-lucide-eye-off' : 'i-lucide-eye'"
            :aria-label="show ? t('public.locked.hide') : t('public.locked.show')"
            color="neutral"
            variant="link"
            size="sm"
            @click="show = !show"
          />
        </template>
      </UInput>
    </UFormField>
    <UButton type="submit" :label="t('public.locked.open')" icon="i-lucide-lock-open" color="neutral" block :loading="busy" :disabled="!password" />
  </form>
</template>

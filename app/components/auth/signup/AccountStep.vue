<!-- Signup step 1: name, email, password (+ strength) → OTP challenge. -->
<script setup lang="ts">
import type { FormSubmitEvent } from '@nuxt/ui'

const emit = defineEmits<{ done: [] }>()
const { t } = useI18n()
const auth = useAuth()
const { busy, run } = useBusy()

const schema = computed(() => signupAccountSchema(t))
const state = reactive({ first_name: '', last_name: '', email: '', password: '' })

async function onSubmit(event: FormSubmitEvent<typeof state>) {
  const ok = await run(async () => {
    await auth.signup(event.data)
    return true
  })
  if (ok) emit('done')
}
</script>

<template>
  <UForm :schema="schema" :state="state" class="flex flex-col gap-4" @submit="onSubmit">
    <div class="grid gap-4 sm:grid-cols-2">
      <UFormField :label="t('auth.fields.firstName')" name="first_name" required>
        <UInput v-model="state.first_name" autocomplete="given-name" size="xl" class="w-full" autofocus />
      </UFormField>
      <UFormField :label="t('auth.fields.lastName')" name="last_name" required>
        <UInput v-model="state.last_name" autocomplete="family-name" size="xl" class="w-full" />
      </UFormField>
    </div>
    <UFormField :label="t('auth.fields.email')" name="email" required>
      <UInput
        v-model="state.email"
        type="email"
        autocomplete="email"
        :placeholder="t('auth.fields.emailPlaceholder')"
        icon="i-lucide-mail"
        size="xl"
        class="w-full"
      />
    </UFormField>
    <UFormField :label="t('auth.fields.password')" name="password" required>
      <AuthPasswordInput
        v-model="state.password"
        autocomplete="new-password"
        size="xl"
        icon="i-lucide-lock-keyhole"
      />
      <AuthPasswordStrength :value="state.password" />
    </UFormField>
    <UButton
      type="submit"
      :label="t('auth.signup.continue')"
      color="neutral"
      size="xl"
      block
      :loading="busy"
    />
  </UForm>
</template>

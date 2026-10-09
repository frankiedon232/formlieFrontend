<!--
  My profile → Password (F16 M5): the current one, then a new one that meets the workspace's rules
  (the meter lists what is missing). Other devices are signed out afterwards.
-->
<script setup lang="ts">
const props = defineProps<{ changedAt: string | null }>()
const emit = defineEmits<{ changed: [] }>()
const { t } = useI18n()
const api = useApi()
const toast = useToast()
const { handle } = useErrorHandler()
const { relative } = useFormat()
const policy = computed(() => useTenant().profile.value?.password_policy)

const state = reactive({ current: '', password: '', confirm: '' })
const schema = computed(() => resetSchema(t, policy.value))
const valid = computed(() => !!state.current && schema.value.safeParse({ password: state.password, confirm: state.confirm }).success)
const saving = ref(false)
async function save() {
  if (!valid.value || saving.value) return
  saving.value = true
  try {
    await api.post('/me/password', { current: state.current, password: state.password })
    Object.assign(state, { current: '', password: '', confirm: '' })
    toast.add({ title: t('profile.password.done'), description: t('profile.password.doneDesc'), color: 'success', icon: 'i-lucide-key-round' })
    emit('changed')
  } catch (error) {
    handle(error)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <SettingsBlock :title="t('profile.password.title')" :description="props.changedAt ? t('profile.password.changedAgo', { when: relative(props.changedAt) }) : t('profile.password.desc')" icon="i-lucide-key-round">
    <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="save">
      <UFormField :label="t('profile.password.current')" class="sm:col-span-2">
        <AuthPasswordInput v-model="state.current" autocomplete="current-password" class="w-full sm:max-w-sm" />
      </UFormField>
      <UFormField :label="t('profile.password.new')">
        <AuthPasswordInput v-model="state.password" autocomplete="new-password" class="w-full" />
        <AuthPasswordStrength :value="state.password" :policy="policy" />
      </UFormField>
      <UFormField :label="t('people.join.confirm')" :error="state.confirm && state.confirm !== state.password ? t('auth.validation.passwordMatch') : undefined">
        <AuthPasswordInput v-model="state.confirm" autocomplete="new-password" class="w-full" />
      </UFormField>
      <div class="sm:col-span-2"><UButton type="submit" :label="t('profile.password.change')" icon="i-lucide-check" color="neutral" :loading="saving" :disabled="!valid" /></div>
    </form>
  </SettingsBlock>
</template>

<!--
  My profile → Your details (F16 M5): photo (picked, made square and small in the browser, up to 256 px)
  and name. The email address is the sign-in and stays as it is; admins change department, job title,
  role and manager on People.
-->
<script setup lang="ts">
import type { MyProfile } from '#shared/types/profile'

const props = defineProps<{ profile: MyProfile; saving: string | null }>()
const emit = defineEmits<{ save: [part: string, values: Partial<MyProfile>, message?: string] }>()
const { t } = useI18n()
const toast = useToast()

const state = reactive({ first_name: props.profile.first_name, last_name: props.profile.last_name })
watch(() => props.profile, value => Object.assign(state, { first_name: value.first_name, last_name: value.last_name }))
const dirty = computed(() => state.first_name.trim() !== props.profile.first_name || state.last_name.trim() !== props.profile.last_name)
const valid = computed(() => !!state.first_name.trim() && !!state.last_name.trim())

const input = useTemplateRef<HTMLInputElement>('file')
/** A square crop from the middle, 256 px, as JPEG: small enough to sit everywhere an avatar shows. */
async function pick(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  ;(event.target as HTMLInputElement).value = ''
  if (!file) return
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) return toast.add({ title: t('profile.photoType'), color: 'warning', icon: 'i-lucide-image-off' })
  try {
    const bitmap = await createImageBitmap(file)
    const side = Math.min(bitmap.width, bitmap.height)
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 256
    canvas.getContext('2d')!.drawImage(bitmap, (bitmap.width - side) / 2, (bitmap.height - side) / 2, side, side, 0, 0, 256, 256)
    emit('save', 'photo', { photo: canvas.toDataURL('image/jpeg', 0.85) }, t('profile.photoSaved'))
  } catch {
    toast.add({ title: t('profile.photoType'), color: 'warning', icon: 'i-lucide-image-off' })
  }
}
</script>

<template>
  <SettingsBlock :title="t('profile.details.title')" :description="t('profile.details.desc')" icon="i-lucide-user-round">
    <div class="flex flex-wrap items-center gap-4">
      <UAvatar :src="profile.photo ?? undefined" :alt="`${profile.first_name} ${profile.last_name}`" size="3xl" class="ring-4 ring-(--ui-bg-elevated)" />
      <div class="flex flex-wrap gap-2">
        <input ref="file" type="file" accept="image/png,image/jpeg,image/webp" class="hidden" @change="pick">
        <UButton :label="profile.photo ? t('profile.photoChange') : t('profile.photoAdd')" icon="i-lucide-image-up" color="neutral" variant="outline" size="sm" :loading="saving === 'photo'" @click="input?.click()" />
        <UButton v-if="profile.photo" :label="t('profile.photoRemove')" icon="i-lucide-trash-2" color="neutral" variant="ghost" size="sm" :disabled="!!saving" @click="emit('save', 'photo', { photo: null }, t('profile.photoRemoved'))" />
      </div>
    </div>
    <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="valid && dirty && emit('save', 'details', { first_name: state.first_name.trim(), last_name: state.last_name.trim() })">
      <UFormField :label="t('auth.fields.firstName')" required :error="!state.first_name.trim() ? t('auth.validation.required') : undefined">
        <UInput v-model="state.first_name" maxlength="60" autocomplete="given-name" class="w-full" />
      </UFormField>
      <UFormField :label="t('auth.fields.lastName')" required :error="!state.last_name.trim() ? t('auth.validation.required') : undefined">
        <UInput v-model="state.last_name" maxlength="60" autocomplete="family-name" class="w-full" />
      </UFormField>
      <UFormField :label="t('auth.fields.email')" :description="t('profile.emailHint')" class="sm:col-span-2">
        <UInput :model-value="profile.email" icon="i-lucide-mail" disabled dir="ltr" class="w-full" />
      </UFormField>
      <div class="sm:col-span-2">
        <UButton type="submit" :label="t('common.save')" icon="i-lucide-check" color="neutral" :loading="saving === 'details'" :disabled="!dirty || !valid" />
      </div>
    </form>
  </SettingsBlock>
</template>

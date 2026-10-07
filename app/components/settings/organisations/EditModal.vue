<!--
  Settings → Organisations (F14 M7): add or change an organisation: name (unique), short name for
  tight places, website and logo (shown on its forms' public pages). Draggable dialog; Enter saves.
-->
<script setup lang="ts">
import type { Organisation } from '#shared/types/organisations'

const props = defineProps<{ item: Organisation | null }>()
const open = defineModel<boolean>('open', { required: true })
const emit = defineEmits<{ saved: [item: Organisation] }>()
const { t } = useI18n()
const api = useApi()
const { busy, run, error } = useBusy()

const state = reactive({ name: '', short_name: null as string | null, website: null as string | null, logo_url: null as string | null })
const logoUpload = ref<string | null | undefined>(undefined)
watch(open, value => {
  if (!value) return
  Object.assign(state, { name: props.item?.name ?? '', short_name: props.item?.short_name ?? null, website: props.item?.website ?? null, logo_url: props.item?.logo_url ?? null })
  logoUpload.value = undefined
})
const nameTaken = computed(() => error.value?.code === 'FRM-ORG-1001')
const websiteBad = computed(() => !!state.website && !/^https?:\/\/[^\s.]+\.[^\s]+$/i.test(state.website))
const valid = computed(() => state.name.trim().length >= 2 && !websiteBad.value)

async function save() {
  if (!valid.value) return
  const body = { name: state.name, short_name: state.short_name, website: state.website, ...(logoUpload.value !== undefined ? { logo_upload_id: logoUpload.value } : {}) }
  const saved = await run(async () => (props.item ? (await api.patch<Organisation>(`/organisations/${props.item.id}`, body)).data : (await api.post<Organisation>('/organisations', body)).data), { silentError: true })
  if (saved) {
    emit('saved', saved)
    open.value = false
  } else if (!nameTaken.value && error.value) useErrorHandler().handle(error.value)
}
</script>

<template>
  <AppModal v-model:open="open" :title="item ? t('organisations.editTitle', { name: item.name }) : t('organisations.new')" :description="t('organisations.editDesc')" keep-open>
    <template #body>
      <form class="flex flex-col gap-4" @submit.prevent="save">
        <UFormField :label="t('organisations.name')" required :error="nameTaken ? t('organisations.nameTaken') : undefined">
          <UInput v-model="state.name" :placeholder="t('organisations.namePlaceholder')" class="w-full" autofocus />
        </UFormField>
        <div class="grid gap-4 sm:grid-cols-2">
          <UFormField :label="t('organisations.shortName')" :help="t('organisations.shortNameHelp')">
            <SettingsText v-model="state.short_name" maxlength="24" class="w-full" />
          </UFormField>
          <UFormField :label="t('organisations.website')" :error="websiteBad ? t('settings.invalid.website') : undefined">
            <SettingsText v-model="state.website" type="url" placeholder="https://www.example.com" class="w-full" />
          </UFormField>
        </div>
        <SettingsPicture v-model:url="state.logo_url" v-model:upload-id="logoUpload" :label="t('organisations.logo')" :hint="t('organisations.logoHint')" purpose="logo" :max-mb="2" />
        <button type="submit" class="hidden" />
      </form>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton :label="t('common.cancel')" color="neutral" variant="outline" @click="open = false" />
        <UButton :label="item ? t('common.save') : t('organisations.create')" icon="i-lucide-check" color="neutral" :loading="busy" :disabled="!valid" @click="save" />
      </div>
    </template>
  </AppModal>
</template>

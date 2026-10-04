<!--
  "Use template" (F9): name the new form and pick its folder, then it opens in the builder,
  every field, rule, calculation and the design can be changed before publishing.
-->
<script setup lang="ts">
import { z } from 'zod'
import type { FormSubmitEvent } from '@nuxt/ui'
import type { FormFolder } from '#shared/types/forms'
import type { TemplateSummary } from '#shared/types/templates'

const props = defineProps<{ template: Pick<TemplateSummary, 'key' | 'name'> | null }>()
const open = defineModel<boolean>('open', { default: false })
const { t } = useI18n()
const api = useApi()
const templates = useTemplates()

const NONE = '__none__'
const schema = z.object({
  name: z.string().trim().min(1, t('templates.nameRequired')).max(120),
  folder: z.string(),
})
const state = reactive({ name: '', folder: NONE })
const folders = ref<FormFolder[]>([])
const foldersLoading = ref(false)

watch(open, async value => {
  if (!value || !props.template) return
  state.name = props.template.name
  state.folder = NONE
  foldersLoading.value = true
  try {
    folders.value = (await api.get<FormFolder[]>('/folders', undefined, { background: true })).data
  } catch {
    // Folder stays "No folder".
  } finally {
    foldersLoading.value = false
  }
})
const folderItems = computed(() => [
  { value: NONE, label: t('forms.noFolder'), icon: 'i-lucide-folder-minus' },
  ...folders.value.map(folder => ({ value: folder.id, label: folder.name, icon: 'i-lucide-folder' })),
])

const { busy, run } = useBusy()
async function submit(event: FormSubmitEvent<z.output<typeof schema>>) {
  if (!props.template) return
  const created = await run(() =>
    templates.use(props.template!, {
      name: event.data.name,
      folder_id: event.data.folder === NONE ? null : event.data.folder,
    }),
  )
  if (created) open.value = false
}
</script>

<template>
  <AppModal
    v-model:open="open"
    :title="t('templates.useTitle')"
    :description="t('templates.useDesc')"
    :dismissible="!busy"
  >
    <template #body>
      <UForm
        id="use-template-form"
        :schema="schema"
        :state="state"
        class="flex flex-col gap-4"
        @submit="submit"
      >
        <UFormField name="name" :label="t('forms.new.name')" required>
          <UInput v-model="state.name" maxlength="120" class="w-full" autofocus />
        </UFormField>
        <UFormField name="folder" :label="t('forms.move.folder')">
          <template #label>
            <AppInfoLabel :label="t('forms.move.folder')" :info="t('forms.new.folderHint')" />
          </template>
          <USelectMenu
            v-model="state.folder"
            :items="folderItems"
            value-key="value"
            :loading="foldersLoading"
            :search-input="{ placeholder: t('common.search') }"
            class="w-full"
          />
        </UFormField>
      </UForm>
    </template>
    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="outline"
          :disabled="busy"
          @click="open = false"
        />
        <UButton
          type="submit"
          form="use-template-form"
          :label="t('templates.use')"
          icon="i-lucide-file-plus"
          color="neutral"
          :loading="busy"
        />
      </div>
    </template>
  </AppModal>
</template>

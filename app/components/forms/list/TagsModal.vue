<!-- Edit a form's tags: type and press Enter, pick an existing tag, or remove one. -->
<script setup lang="ts">
const props = defineProps<{ tags: string[]; suggestions: string[]; formName: string }>()
const open = defineModel<boolean>('open', { default: false })
const emit = defineEmits<{ save: [tags: string[]] }>()
const { t } = useI18n()

const value = ref<string[]>([])
watch(open, isOpen => {
  if (isOpen) value.value = [...props.tags]
})

const unused = computed(() => props.suggestions.filter(tag => !value.value.includes(tag)).slice(0, 12))
const normalise = (tags: string[]) =>
  [...new Set(tags.map(tag => tag.trim().toLowerCase()).filter(Boolean))].slice(0, 20)

function save() {
  emit('save', normalise(value.value))
  open.value = false
}
</script>

<template>
  <AppModal v-model:open="open" :title="t('forms.tags.title')" :description="formName">
    <template #body>
      <div class="flex flex-col gap-4">
        <UFormField :label="t('forms.tags.label')" :hint="t('forms.tags.hint')">
          <UInputTags
            v-model="value"
            :max-length="30"
            :placeholder="t('forms.tags.placeholder')"
            class="w-full"
          />
        </UFormField>
        <div v-if="unused.length" class="flex flex-wrap items-center gap-1.5">
          <span class="me-1 text-xs text-muted">{{ t('forms.tags.existing') }}</span>
          <UButton
            v-for="tag in unused"
            :key="tag"
            :label="tag"
            icon="i-lucide-plus"
            color="neutral"
            variant="outline"
            size="xs"
            @click="value = normalise([...value, tag])"
          />
        </div>
      </div>
    </template>
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton
          :label="t('common.cancel')"
          color="neutral"
          variant="outline"
          class="justify-center"
          @click="open = false"
        />
        <UButton
          :label="t('common.save')"
          icon="i-lucide-check"
          color="neutral"
          class="justify-center"
          @click="save"
        />
      </div>
    </template>
  </AppModal>
</template>

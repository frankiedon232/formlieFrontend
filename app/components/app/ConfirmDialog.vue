<!--
  Confirmation for destructive / important actions (CLAUDE.md rule 13). Mounted once in the
  layouts and driven by useConfirm(). Draggable like every AppModal; Esc / outside = cancel.
  Always the top layer, it can open from a drawer or slide-over (designer controls on phones).
-->
<script setup lang="ts">
const { t } = useI18n()
const { pending: request, settle } = useConfirmState()
// Keep the last request on screen while the dialog fades out (no blank title / default labels).
const shown = shallowRef(request.value)
watch(request, value => value && (shown.value = value))
const pending = computed(() => shown.value)

const open = computed({
  get: () => !!request.value,
  set: value => {
    if (!value) settle(false)
  },
})
</script>

<template>
  <AppModal v-model:open="open" :title="pending?.title ?? ''" :description="pending?.description" :ui="{ overlay: 'z-[60]', content: 'z-[60]' }">
    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <UButton
          :label="pending?.cancelLabel ?? t('common.cancel')"
          color="neutral"
          variant="outline"
          class="justify-center"
          @click="settle(false)"
        />
        <UButton
          :label="pending?.confirmLabel ?? t('common.confirm')"
          :color="pending?.danger ? 'error' : 'neutral'"
          :icon="pending?.danger ? 'i-lucide-trash-2' : undefined"
          class="justify-center"
          autofocus
          @click="settle(true)"
        />
      </div>
    </template>
  </AppModal>
</template>

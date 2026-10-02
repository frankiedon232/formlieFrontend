<!--
  Confirmation for destructive / important actions (CLAUDE.md rule 13). Mounted once in the
  layouts and driven by useConfirm(). Draggable like every AppModal; Esc / outside = cancel.
-->
<script setup lang="ts">
const { t } = useI18n()
const { pending, settle } = useConfirmState()

const open = computed({
  get: () => !!pending.value,
  set: value => {
    if (!value) settle(false)
  },
})
</script>

<template>
  <AppModal v-model:open="open" :title="pending?.title ?? ''" :description="pending?.description">
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

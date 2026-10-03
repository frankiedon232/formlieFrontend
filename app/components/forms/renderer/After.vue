<!--
  After sending, on the public form (owner, 2026-10-03):
    thanks  — under the thank-you message: "Fill in another" and "Close this page"
    already — this browser already sent the form: say so, offer "Fill in for someone else"
  Filling in again always asks first: it must be for another person (the same person's response is
  accepted once). "Close this page" closes the tab where the browser allows it, otherwise it says
  the tab can be closed now.
-->
<script setup lang="ts">
const props = defineProps<{ mode: 'thanks' | 'already' }>()
const emit = defineEmits<{ another: [] }>()
const { t } = useI18n()

const asking = ref(false)
function confirmAnother() {
  asking.value = false
  emit('another')
}

const closeHint = ref(false)
function closePage() {
  window.close()
  // Browsers only let a page close a tab it opened itself; otherwise say it can be closed now.
  setTimeout(() => (closeHint.value = !window.closed), 300)
}
</script>

<template>
  <div class="flex flex-col items-center gap-3">
    <template v-if="props.mode === 'already'">
      <span class="flex size-12 items-center justify-center rounded-full bg-elevated">
        <UIcon name="i-lucide-badge-check" class="size-6 text-(--ui-primary)" />
      </span>
      <h2 class="text-xl font-semibold text-highlighted">{{ t('renderer.after.alreadyTitle') }}</h2>
      <p class="max-w-md text-sm text-muted">{{ t('renderer.after.alreadyDesc') }}</p>
    </template>

    <div class="flex flex-col-reverse items-stretch gap-2 pt-1 sm:flex-row sm:items-center">
      <UButton :label="t('renderer.after.close')" icon="i-lucide-x" color="neutral" variant="outline" class="justify-center" @click="closePage" />
      <UButton
        :label="props.mode === 'already' ? t('renderer.after.forSomeoneElse') : t('renderer.after.another')"
        icon="i-lucide-user-plus"
        color="primary"
        class="justify-center rounded-[var(--form-button-radius)]"
        @click="asking = true"
      />
    </div>
    <p v-if="closeHint" class="text-xs text-muted" role="status">{{ t('renderer.after.closeHint') }}</p>

    <AppModal v-model:open="asking" :title="t('renderer.after.askTitle')" :description="t('renderer.after.askDesc')">
      <template #body>
        <ul class="flex flex-col gap-2 text-sm text-default">
          <li class="flex items-start gap-2"><UIcon name="i-lucide-user-check" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('renderer.after.askPoint1') }}</li>
          <li class="flex items-start gap-2"><UIcon name="i-lucide-copy-x" class="mt-0.5 size-4 shrink-0 text-muted" />{{ t('renderer.after.askPoint2') }}</li>
        </ul>
      </template>
      <template #footer>
        <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <UButton :label="t('renderer.after.stay')" color="neutral" variant="outline" class="justify-center" @click="asking = false" />
          <UButton :label="t('renderer.after.confirm')" icon="i-lucide-user-plus" color="neutral" class="justify-center" @click="confirmAnother" />
        </div>
      </template>
    </AppModal>
  </div>
</template>

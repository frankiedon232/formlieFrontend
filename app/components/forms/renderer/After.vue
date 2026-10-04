<!--
  After sending, on the public form (owner, 2026-10-03 / 2026-10-04):
    thanks, under the thank-you message: "Fill in another", "Visit {org}'s website" (when it has
            one) and "All done. You can close this tab."
    already, this browser already sent the form: say so, offer "Fill in for someone else"
  Every button always works (owner): browsers only let a page close a tab that a script opened, so
  "Close this page" shows only then; otherwise a clear line says the tab can be closed. Embedded in
  another website: no close and no website button (the visitor stays on that site).
  Filling in again always asks first: it must be for another person.
-->
<script setup lang="ts">
const props = defineProps<{ mode: 'thanks' | 'already'; org?: { name: string; website: string | null }; embedded?: boolean }>()
const emit = defineEmits<{ another: [] }>()
const { t } = useI18n()

const asking = ref(false)
function confirmAnother() {
  asking.value = false
  emit('another')
}

/** Opened by another page (a pop-up or window it opened): only then may this page close itself. */
const canClose = ref(false)
onMounted(() => (canClose.value = !props.embedded && !!window.opener))
const closePage = () => window.close()
const website = computed(() => (!props.embedded && props.org?.website ? props.org.website : null))
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
      <UButton v-if="canClose" :label="t('renderer.after.close')" icon="i-lucide-x" color="neutral" variant="outline" class="justify-center" @click="closePage" />
      <UButton
        v-else-if="website"
        :to="website"
        external
        :label="t('renderer.after.visit', { org: org?.name })"
        trailing-icon="i-lucide-arrow-up-right"
        color="neutral"
        variant="outline"
        class="justify-center"
      />
      <UButton
        :label="props.mode === 'already' ? t('renderer.after.forSomeoneElse') : t('renderer.after.another')"
        icon="i-lucide-user-plus"
        color="primary"
        class="justify-center rounded-[var(--form-button-radius)]"
        @click="asking = true"
      />
    </div>
    <!-- Always clear what to do next, also when the tab can't close itself. -->
    <p v-if="props.mode === 'thanks' && !canClose && !embedded" class="flex items-center gap-1.5 text-xs text-muted" role="status">
      <UIcon name="i-lucide-circle-check" class="size-3.5" />{{ t('renderer.after.done') }}
    </p>

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

<!-- Temporary body for sections whose roadmap phase hasn't started. -->
<script setup lang="ts">
const props = defineProps<{
  icon: string
  titleKey: string
  /** What the section will do (defaults to "This section is being built."). */
  descriptionKey?: string
  /** Where to go meanwhile (defaults to Forms). */
  back?: { labelKey: string; icon: string; to: string }
}>()
const { t } = useI18n()
const back = computed(() => props.back ?? { labelKey: 'nav.forms', icon: 'i-lucide-file-text', to: '/forms' })
</script>

<template>
  <AppEmpty
    :icon="props.icon"
    :title="t(props.titleKey)"
    :description="t(props.descriptionKey ?? 'placeholder.description')"
    :actions="[
      {
        label: t(back.labelKey),
        icon: back.icon,
        to: back.to,
        color: 'neutral',
        variant: 'subtle',
      },
    ]"
    class="my-auto"
  />
</template>

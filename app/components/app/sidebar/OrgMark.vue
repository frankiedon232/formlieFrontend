<!--
  The organisation in the rail (F5, owner 2026-10-10): its logo above Help & support, with its name in the
  tooltip, so people see whose workspace they work in. The dark-background logo in a dark rail or dark mode;
  without a logo, its initials on its brand colour. Admins open Settings → Branding from it.
-->
<script setup lang="ts">
const props = defineProps<{ dark?: boolean }>()
const { t } = useI18n()
const { profile } = useTenant()
const { can } = useCan()
const colorMode = useColorMode()

const name = computed(() => profile.value?.name ?? '')
const onDark = computed(() => props.dark || colorMode.value === 'dark')
/** A logo made for dark backgrounds sits on the dark surface; the normal one on a white tile, readable in both modes. */
const darkLogo = computed(() => (onDark.value ? (profile.value?.logo_dark_url ?? null) : null))
const logo = computed(() => darkLogo.value ?? profile.value?.logo_url ?? null)
const initials = computed(() =>
  name.value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]!.toUpperCase())
    .join(''),
)
const brand = computed(() => profile.value?.colors.primary ?? null)
// Logos that fail to load fall back to the initials
const broken = ref(false)
watch(logo, () => (broken.value = false))
</script>

<template>
  <UTooltip v-if="name" :text="name" :content="{ side: 'right' }">
    <component
      :is="can('settings.manage') ? 'NuxtLink' : 'span'"
      :to="can('settings.manage') ? '/settings/branding' : undefined"
      class="flex size-10 items-center justify-center overflow-hidden rounded-(--ui-radius) border border-default p-1 focus-visible:outline-2 focus-visible:outline-(--ui-border-inverted)"
      :class="logo && !broken ? (darkLogo ? 'bg-elevated' : 'bg-white') : 'border-transparent'"
      :style="logo && !broken ? undefined : { backgroundColor: brand ?? 'var(--ui-bg-inverted)' }"
      :aria-label="can('settings.manage') ? t('nav.orgBranding', { name }) : name"
    >
      <img v-if="logo && !broken" :src="logo" :alt="name" class="size-full object-contain" @error="broken = true">
      <span v-else class="text-xs font-semibold" :class="brand ? 'text-white' : 'text-inverted'">{{ initials }}</span>
    </component>
  </UTooltip>
</template>

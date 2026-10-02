<!-- Designer groups: Header (cover, logo, title, subtitle, alignment) · Footer (text, links, logo) · Thank-you page. -->
<script setup lang="ts">
import type { FormTheme } from '#shared/utils/forms/theme'

defineProps<{ group: 'header' | 'footer' | 'thank_you' }>()
const { t } = useI18n()
const d = useDesigner()
const theme = d.theme
const branding = useWorkspaceBranding()

const align = computed(() => [
  { value: 'start', label: t('builder.blocks.alignStart') },
  { value: 'center', label: t('builder.blocks.alignCenter') },
])
const heights = computed(() => ['sm', 'md', 'lg'].map(value => ({ value, label: t(`designer.size.${value}`) })))

// Footer links: label + https link, up to 6.
type Link = FormTheme['footer']['links'][number]
const links = computed(() => theme.value.footer.links)
const linkError = (href: string) => (href && !/^https:\/\/\S+$/i.test(href) ? t('builder.blocks.linkInvalid') : undefined)
function setLink(index: number, patch: Partial<Link>) {
  d.set('footer', 'links', links.value.map((link, i) => (i === index ? { ...link, ...patch } : link)))
}
const addLink = () => d.set('footer', 'links', [...links.value, { label: t('designer.footer.newLink'), href: 'https://' }])
const removeLink = (index: number) => d.set('footer', 'links', links.value.filter((_, i) => i !== index))
</script>

<template>
  <div class="flex flex-col gap-4">
    <template v-if="group === 'header'">
      <FormsDesignerImageField :label="t('designer.header.cover')" :hint="t('designer.header.coverHint')" :model-value="theme.header.cover" @update:model-value="v => d.set('header', 'cover', v)" />
      <FormsDesignerChoice v-if="theme.header.cover" :label="t('designer.header.coverHeight')" :model-value="theme.header.cover_height" :items="heights" @update:model-value="v => d.set('header', 'cover_height', v as 'sm' | 'md' | 'lg')" />
      <USwitch :model-value="theme.header.show_logo" :label="t('designer.header.showLogo')" color="neutral" @update:model-value="v => d.set('header', 'show_logo', v)" />
      <FormsDesignerImageField
        v-if="theme.header.show_logo"
        :label="t('designer.header.logo')"
        :hint="branding.logo_url ? t('designer.header.logoHint') : t('designer.header.logoNone')"
        :model-value="theme.header.logo"
        @update:model-value="v => d.set('header', 'logo', v)"
      />
      <USwitch :model-value="theme.header.show_title" :label="t('designer.header.showTitle')" color="neutral" @update:model-value="v => d.set('header', 'show_title', v)" />
      <UFormField :label="t('designer.header.subtitle')">
        <UTextarea :model-value="theme.header.subtitle" :rows="2" autoresize maxlength="300" class="w-full" @update:model-value="v => d.set('header', 'subtitle', String(v))" />
      </UFormField>
      <FormsDesignerChoice :label="t('builder.blocks.align')" :model-value="theme.header.align" :items="align" @update:model-value="v => d.set('header', 'align', v as 'start' | 'center')" />
    </template>

    <template v-if="group === 'footer'">
      <USwitch :model-value="theme.footer.enabled" :label="t('designer.footer.show')" color="neutral" @update:model-value="v => d.set('footer', 'enabled', v)" />
      <template v-if="theme.footer.enabled">
        <UFormField :label="t('designer.footer.text')" :description="t('designer.footer.textHint')">
          <UTextarea :model-value="theme.footer.text" :rows="2" autoresize maxlength="500" class="w-full" @update:model-value="v => d.set('footer', 'text', String(v))" />
        </UFormField>
        <div class="flex flex-col gap-2">
          <p class="text-sm font-medium text-highlighted">{{ t('designer.footer.links') }}</p>
          <div v-for="(link, i) in links" :key="i" class="flex flex-col gap-1.5 rounded-md border border-default p-2">
            <div class="flex items-center gap-1">
              <UInput :model-value="link.label" size="sm" maxlength="60" class="min-w-0 flex-1" :aria-label="t('designer.footer.linkLabel', { n: i + 1 })" @update:model-value="v => setLink(i, { label: String(v) })" />
              <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="xs" square :aria-label="t('designer.footer.removeLink', { n: i + 1 })" @click="removeLink(i)" />
            </div>
            <UFormField :error="linkError(link.href)">
              <UInput :model-value="link.href" type="url" size="sm" icon="i-lucide-link" class="w-full" :aria-label="t('designer.footer.linkUrl', { n: i + 1 })" @update:model-value="v => setLink(i, { href: String(v) })" />
            </UFormField>
          </div>
          <UButton :label="t('designer.footer.addLink')" icon="i-lucide-plus" color="neutral" variant="outline" size="sm" class="self-start" :disabled="links.length >= 6" @click="addLink" />
        </div>
        <USwitch :model-value="theme.footer.show_logo" :label="t('designer.footer.showLogo')" color="neutral" @update:model-value="v => d.set('footer', 'show_logo', v)" />
        <FormsDesignerChoice :label="t('builder.blocks.align')" :model-value="theme.footer.align" :items="align" @update:model-value="v => d.set('footer', 'align', v as 'start' | 'center')" />
      </template>
    </template>

    <template v-if="group === 'thank_you'">
      <p class="text-xs text-muted">{{ t('designer.thankYouHint') }}</p>
      <USwitch :model-value="theme.thank_you.show_icon" :label="t('designer.showTick')" color="neutral" @update:model-value="v => d.set('thank_you', 'show_icon', v)" />
    </template>
  </div>
</template>

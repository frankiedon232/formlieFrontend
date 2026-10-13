<script setup lang="ts">
import type { NuxtError } from '#app'

// 404 and other errors, inside the normal header and footer.
const props = defineProps<{ error: NuxtError }>()

const { t } = useI18n()
const localePath = useLocalePath()
const links = useSiteLinks()

const notFound = computed(() => props.error.statusCode === 404)

useSeoMeta({
  title: () => `${notFound.value ? t('error.notFoundTitle') : t('error.title')} · ${t('site.name')}`,
  robots: 'noindex',
})
</script>

<template>
  <UApp>
    <NuxtLayout>
      <UError
        :error="{
          statusCode: error.statusCode,
          statusMessage: notFound ? t('error.notFoundTitle') : t('error.title'),
          message: notFound ? t('error.notFoundText') : t('error.text'),
        }"
        :clear="false"
        :ui="{ root: 'min-h-[60vh]' }"
      >
        <template #links>
          <div class="mt-8 flex flex-wrap items-center justify-center gap-3">
            <UButton :to="localePath('/')" :label="t('error.home')" color="neutral" size="lg" />
            <UButton
              :to="`${links.portal}/help`"
              target="_blank"
              :label="t('error.help')"
              color="neutral"
              variant="outline"
              size="lg"
            />
          </div>
        </template>
      </UError>
    </NuxtLayout>
  </UApp>
</template>

<script setup lang="ts">
// One of Formalie's own published forms, embedded (docs/API-HOOKS.md, CLAUDE.md rule 7): never a hand-made form.
// The embed tells the page its height (`formalie:resize`), that someone started typing (`formalie:typing`) and
// that it was sent (`formalie:submitted`); only messages from the forms origin about this form are read. It opens
// in the visitor's language (`?lang=`) with the values the site may prefill.
const props = defineProps<{
  formKey: FormKey
  /** The form's name, for the frame's accessible title. */
  name: string
  prefill?: Record<string, string | undefined>
}>()

const { t, locale } = useI18n()
const toast = useToast()
const links = useSiteLinks()
const config = useRuntimeConfig().public

const src = computed(() => links.formEmbed(props.formKey, { ...props.prefill, lang: locale.value }))
const origin = new URL(config.formsUrl).origin

const height = ref(0)
const loaded = ref(false)
const sent = ref(false)
const failed = ref(false)

function onMessage(event: MessageEvent) {
  if (event.origin !== origin) return
  const data = event.data as { type?: string; key?: string; height?: number }
  if (!data || data.key !== props.formKey) return
  if (data.type === 'formalie:resize' && typeof data.height === 'number') {
    height.value = Math.max(320, Math.ceil(data.height))
    loaded.value = true
  }
  if (data.type === 'formalie:submitted' && !sent.value) {
    sent.value = true
    toast.add({
      title: t('embed.thanksTitle'),
      description: t('embed.thanksText'),
      icon: 'i-lucide-circle-check',
      color: 'success',
    })
  }
}

useEventListener(import.meta.client ? window : undefined, 'message', onMessage)

// If the form never answers (portal down, blocked network), say so and offer email instead.
onMounted(() => {
  setTimeout(() => {
    if (!loaded.value) failed.value = true
  }, 15000)
})
</script>

<template>
  <div>
    <div class="relative overflow-hidden rounded-3xl bg-default shadow-xl shadow-black/5 ring-1 ring-default">
      <!-- Loading: a calm skeleton of a form while the embed starts -->
      <div v-if="!loaded" class="absolute inset-0 flex flex-col gap-4 p-6 sm:p-8" aria-hidden="true">
        <USkeleton class="h-6 w-1/2" />
        <USkeleton class="h-4 w-3/4" />
        <USkeleton v-for="i in 4" :key="i" class="h-11 w-full" />
        <USkeleton class="h-11 w-32" />
      </div>
      <p v-if="!loaded && !failed" class="sr-only" role="status">{{ t('embed.loading') }}</p>

      <UAlert
        v-if="failed && !loaded"
        icon="i-lucide-mail"
        color="neutral"
        variant="subtle"
        class="relative m-6"
      >
        <template #description>
          <i18n-t keypath="embed.unavailable" tag="span" scope="global">
            <template #email>
              <a href="mailto:support@formalie.com" class="font-semibold underline underline-offset-4"
                >support@formalie.com</a
              >
            </template>
          </i18n-t>
        </template>
      </UAlert>

      <iframe
        :src="src"
        :title="t('embed.frameTitle', { form: name })"
        loading="lazy"
        referrerpolicy="strict-origin-when-cross-origin"
        allow="clipboard-write"
        class="relative block w-full border-0 transition-[height,opacity] duration-300"
        :class="loaded ? 'opacity-100' : 'opacity-0'"
        :style="{ height: `${height || 640}px` }"
      />
    </div>
    <p class="mt-3 flex items-start gap-2 text-xs text-muted">
      <UIcon name="i-formalie-mark" class="mt-0.5 size-3.5 shrink-0" />
      {{ t('embed.own') }}
    </p>
  </div>
</template>

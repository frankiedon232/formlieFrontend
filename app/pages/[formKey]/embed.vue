<!-- Public form for iframes: https://{forms | sub}.formalie.com/{formKey}/embed — no page chrome, auto-resizes (F10). -->
<script setup lang="ts">
import { FORM_KEY_PATTERN } from '#shared/utils/urls/public'

definePageMeta({
  layout: 'public',
  auth: false,
  public: true,
  validate: route => FORM_KEY_PATTERN.test(String(route.params.formKey ?? '')),
})
const route = useRoute()
</script>

<template>
  <PublicFormView :form-key="String(route.params.formKey)" embed />
</template>

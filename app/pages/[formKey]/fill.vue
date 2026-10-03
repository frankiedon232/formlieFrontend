<!-- Public form, full page: https://{forms | sub}.formalie.com/{formKey}/fill (server-rendered, F10). -->
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
  <PublicFormView :form-key="String(route.params.formKey)" />
</template>

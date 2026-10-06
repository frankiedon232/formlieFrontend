<!-- An endpoint's own address (breadcrumbs, shared links): opens it in the Endpoints list's panel. -->
<script setup lang="ts">
definePageMeta({
  breadcrumb: 'nav.apiEndpoints',
  middleware: to => navigateTo({ path: '/api-service/endpoints', query: { endpoint: String(to.params.id) } }, { replace: true }),
})
</script>

<template>
  <div />
</template>

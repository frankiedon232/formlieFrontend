<!-- A connection's own address (breadcrumbs, shared links): opens it in the Connections list's panel. -->
<script setup lang="ts">
definePageMeta({
  breadcrumb: 'nav.dataConnections',
  middleware: to => navigateTo({ path: '/data-sources/connections', query: { connection: String(to.params.id) } }, { replace: true }),
})
</script>

<template>
  <div />
</template>

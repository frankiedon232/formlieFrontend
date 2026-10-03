<!-- Public form renderer (/{formKey}/fill · /embed on forms.* and workspace hosts). The form theme is applied as CSS variables by the renderer root (F10). -->
<template>
  <div class="min-h-dvh">
    <slot />
    <!-- Confirmations on public pages (e.g. "fill in for someone else"). -->
    <AppConfirmDialog />
  </div>
</template>

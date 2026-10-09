<!-- A person's status (F16): Active · Invited · Disabled; an invitation past its 7 days reads "Invite expired". -->
<script setup lang="ts">
import type { PersonRow } from '#shared/types/people'

defineProps<{ person: Pick<PersonRow, 'status' | 'invite'> }>()
const { t } = useI18n()
</script>

<template>
  <DataStatusBadge v-if="person.invite?.expired" status="expired" :label="t('people.invite.expired')" />
  <DataStatusBadge v-else :status="person.status" :label="t(`people.status.${person.status}`)" />
</template>

<!-- A person's status (F16): Active · Not activated · Invited · Awaiting approval · Disabled; a link past its 7 days reads "Link expired". -->
<script setup lang="ts">
import type { PersonRow } from '#shared/types/people'

defineProps<{ person: Pick<PersonRow, 'status' | 'invite'> }>()
const { t } = useI18n()
</script>

<template>
  <DataStatusBadge v-if="person.invite?.expired" status="expired" :label="t('people.invite.expired')" />
  <DataStatusBadge v-else :status="person.status === 'pending' ? 'pending_approval' : person.status" :label="t(`people.status.${person.status}`)" />
</template>

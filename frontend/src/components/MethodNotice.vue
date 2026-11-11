<template>
  <!-- The backend decides whether two GWP totals compare; this only says so. The
       figures stay on the page either way. -->
  <p v-if="comparison.comparability === 'methods_differ'" class="method-notice method-notice--differ" role="note">
    The two buildings use different LCIA methods, {{ comparison.a.lcia_methodology }} and
    {{ comparison.b.lcia_methodology }}: their carbon figures do not compare one to one. {{ comparison.method_note }}
  </p>
  <p v-else-if="comparison.comparability === 'method_not_declared'" class="method-notice" role="note">
    At least one of the two buildings does not declare its LCIA method, so whether their carbon figures compare is
    unknown.
  </p>
</template>

<script setup lang="ts">
import type { Comparison } from '@/api/buildings';

defineProps<{ comparison: Comparison }>();
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.method-notice {
  margin: 0;
  padding: tokens.$spacing-sm tokens.$spacing-lg;
  background: tokens.$color-surface-highlight;
  font-size: tokens.$text-size-sm;
}

.method-notice--differ {
  border-left: 4px solid tokens.$color-status-warning;
}
</style>

<template>
  <div class="results-view">
    <RankedBars :bars="bars" :caption="caption" :empty-label="emptyLabel" />

    <q-table
      flat
      bordered
      hide-bottom
      :rows="rows"
      :columns="columns"
      :row-key="rowKey"
      :pagination="{ rowsPerPage: 0 }"
      :no-data-label="emptyLabel"
    />
  </div>
</template>

<script setup lang="ts" generic="Row extends object">
import type { QTableColumn } from 'quasar';
import RankedBars, { type Bar } from './RankedBars.vue';

defineProps<{
  bars: Bar[];
  rows: Row[];
  columns: QTableColumn<Row>[];
  rowKey: string | ((row: Row) => string);
  caption: string;
  emptyLabel: string;
}>();

</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

// Chart (overview) above table (detail); side by side, the table clips its columns.
.results-view {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}
</style>

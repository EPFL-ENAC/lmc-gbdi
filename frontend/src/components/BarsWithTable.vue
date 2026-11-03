<template>
  <div class="results-view">
    <RankedBars :bars="bars" :caption="caption" :empty-label="emptyLabel" />

    <q-table
      flat
      bordered
      hide-bottom
      :rows="open ? [...rows, ...(rest ?? [])] : rows"
      :columns="columns"
      :row-key="rowKey"
      :pagination="{ rowsPerPage: 0 }"
      :no-data-label="emptyLabel"
    />
    <ShowMore v-if="rest" v-model="open" :count="rest.length" />
  </div>
</template>

<script setup lang="ts" generic="Row extends object">
import { ref } from 'vue';
import type { QTableColumn } from 'quasar';
import ShowMore from '@/components/atoms/ShowMore.vue';
import RankedBars, { type Bar } from './RankedBars.vue';

defineProps<{
  bars: Bar[];
  rows: Row[];
  columns: QTableColumn<Row>[];
  rowKey: string | ((row: Row) => string);
  caption: string;
  emptyLabel: string;
  rest?: Row[]; // rows the chart leaves out, listed in the table on request
}>();
const open = ref(false);

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

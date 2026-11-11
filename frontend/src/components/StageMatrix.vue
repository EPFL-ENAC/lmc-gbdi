<template>
  <!-- Rows (elements or materials) × stage. Emissions are grey, the darker the heavier;
       a credit is green, since more is not better (org#90). -->
  <table class="matrix">
    <caption class="matrix__caption">
      {{ units.carbon }}. Each cell is shaded by its size against the largest cell:
      <ul class="matrix__legend">
        <li v-for="item in LEGEND" :key="item.shade">
          <span class="matrix__swatch" :class="`matrix__cell--${item.shade}`" />{{ item.label }}
        </li>
      </ul>
    </caption>
    <thead>
      <tr>
        <th scope="col">{{ rowHeader }}</th>
        <th v-for="stage in stages" :key="stage.key" scope="col" class="num"><Term :name="stage.label" /></th>
        <th v-if="dominant" scope="col" class="num">Dominant</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.key">
        <th scope="row">{{ row.label }}</th>
        <td
          v-for="stage in stages"
          :key="stage.key"
          class="num"
          :class="`matrix__cell--${shade(row.gwp_by_stage[stage.key])}`"
        >
          {{ num.format(row.gwp_by_stage[stage.key]) }}
        </td>
        <td v-if="dominant" class="num">{{ row.dominant_stage }} {{ percent.format(row.dominant_share ?? 0) }}</td>
      </tr>
      <tr v-if="rows.length === 0">
        <td :colspan="stages.length + (dominant ? 2 : 1)" class="u-text-muted">{{ emptyLabel }}</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { StageTotal, Units } from '@/api/overview';
import Term from '@/components/atoms/Term.vue';
import { amount, percent } from '@/format';

export interface StageRow {
  key: string;
  label: string;
  gwp_by_stage: Record<string, number>;
  dominant_stage?: string; // from the backend; the column shows only when rows carry it
  dominant_share?: number;
}

const props = defineProps<{
  stages: StageTotal[];
  rows: StageRow[];
  units: Units;
  rowHeader: string;
  emptyLabel: string;
}>();
const num = computed(() => amount(props.units));
const dominant = computed(() => props.rows.some((row) => row.dominant_stage !== undefined));

// Shading geometry only: three steps of the grey ramp, each with an AA text colour.
const largest = computed(() =>
  Math.max(...props.rows.flatMap((row) => Object.values(row.gwp_by_stage).map(Math.abs))),
);
// The steps, read by both the shading and its legend.
const STEPS = [
  { shade: 'dark', from: 0.5, label: 'half the largest or more' },
  { shade: 'light', from: 0.15, label: '15 to 50%' },
  { shade: 'pastel', from: 0.02, label: '2 to 15%' },
  { shade: 'none', from: 0, label: 'under 2%' },
] as const;
const LEGEND = [...STEPS, { shade: 'negative', label: 'negative, a credit' }];
const shade = (value: number) =>
  value < 0 ? 'negative' : (STEPS.find((step) => value / largest.value >= step.from)?.shade ?? 'none');
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.matrix {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}

.matrix__caption {
  caption-side: bottom;
  padding-top: tokens.$spacing-sm;
  text-align: left;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.matrix th,
.matrix td {
  padding: tokens.$spacing-sm tokens.$spacing-md;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
}

.matrix thead th {
  font-weight: tokens.$text-weight-medium;
}

.matrix tbody th {
  font-weight: tokens.$text-weight-regular;
}

.matrix .num {
  text-align: right;
}

.matrix__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-xs tokens.$spacing-lg;
  margin: tokens.$spacing-xs 0 0;
  padding: 0;
  list-style: none;
}

.matrix__legend li {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-xs;
}

.matrix__swatch {
  width: tokens.$spacing-md;
  height: tokens.$spacing-md;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-xs;
}

// Black on Grey Pastel: 8:1, on Grey Text: 6:1. White on Grey Dark: 5.9:1.
.matrix__cell--pastel {
  background: var(--gbdi-dataviz-grey-3);
}

.matrix__cell--light {
  background: var(--gbdi-dataviz-grey-2);
}

.matrix__cell--dark {
  background: var(--gbdi-dataviz-grey-1);
  color: tokens.$color-text-on-primary;
}

// A credit is the good cell. Black on Green Light: 6.8:1.
.matrix__cell--negative {
  background: var(--gbdi-dataviz-green-3);
}
</style>

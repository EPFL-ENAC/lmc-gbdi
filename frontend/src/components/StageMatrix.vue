<template>
  <!-- Element × stage, each cell shaded by its size: the darker, the heavier. -->
  <table class="matrix">
    <caption class="matrix__caption">kg CO₂e. Shade: the cell's size against the largest cell.</caption>
    <thead>
      <tr>
        <th scope="col">Element</th>
        <th v-for="stage in stages" :key="stage.key" scope="col" class="num">{{ stage.label }}</th>
        <th scope="col" class="num">Dominant</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="row in rows" :key="row.element">
        <th scope="row">{{ row.element }}</th>
        <td
          v-for="stage in stages"
          :key="stage.key"
          class="num"
          :class="`matrix__cell--${shade(row.gwp_by_stage[stage.key])}`"
        >
          {{ kg.format(row.gwp_by_stage[stage.key]) }}
        </td>
        <td class="num">{{ row.dominant_stage }} {{ percent.format(row.dominant_share) }}</td>
      </tr>
      <tr v-if="rows.length === 0">
        <td :colspan="stages.length + 2" class="u-text-muted">No classified building elements in this project.</td>
      </tr>
    </tbody>
  </table>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ElementStages, StageTotal } from '@/api/overview';
import { kg, percent } from '@/format';

const props = defineProps<{ stages: StageTotal[]; rows: ElementStages[] }>();

// Shading geometry only: three steps of the green ramp, each with an AA text colour
// (Green Bright is skipped: neither Black nor white reaches 4.5:1 on it).
const largest = computed(() =>
  Math.max(...props.rows.flatMap((row) => Object.values(row.gwp_by_stage).map(Math.abs))),
);
const shade = (value: number) => {
  if (value < 0) return 'negative';
  const ratio = value / largest.value;
  if (ratio >= 0.5) return 'dark';
  if (ratio >= 0.15) return 'light';
  if (ratio >= 0.02) return 'pastel';
  return 'none';
};
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

.matrix__cell--pastel {
  background: var(--gbdi-dataviz-green-4);
}

.matrix__cell--light {
  background: var(--gbdi-dataviz-green-3);
}

// White on Green Dark: 6.2:1. Black on Green Light: 6.8:1.
.matrix__cell--dark {
  background: var(--gbdi-dataviz-green-1);
  color: tokens.$color-text-on-primary;
}

.matrix__cell--negative {
  background: var(--gbdi-dataviz-orange-4);
}
</style>

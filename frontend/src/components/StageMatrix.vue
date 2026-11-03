<template>
  <!-- Element × stage, each cell shaded by its size: the darker, the heavier. -->
  <table class="matrix">
    <caption class="matrix__caption">
      kg CO₂e. Each cell is shaded by its size against the largest cell:
      <ul class="matrix__legend">
        <li v-for="item in LEGEND" :key="item.shade">
          <span class="matrix__swatch" :class="`matrix__cell--${item.shade}`" />{{ item.label }}
        </li>
      </ul>
    </caption>
    <thead>
      <tr>
        <th scope="col">Element</th>
        <th v-for="stage in stages" :key="stage.key" scope="col" class="num"><Term :name="stage.label" /></th>
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
import Term from '@/components/atoms/Term.vue';
import { kg, percent } from '@/format';

const props = defineProps<{ stages: StageTotal[]; rows: ElementStages[] }>();

// Shading geometry only: three steps of the green ramp, each with an AA text colour
// (Green Bright is skipped: neither Black nor white reaches 4.5:1 on it).
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

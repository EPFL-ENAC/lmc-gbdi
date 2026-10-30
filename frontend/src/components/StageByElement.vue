<template>
  <div class="results-view">
    <figure class="gbdi-card stage-chart" aria-label="Life-cycle stage by building element, kg CO₂e">
      <ul class="stage-chart__legend">
        <li v-for="(stage, i) in stages" :key="stage.key">
          <span class="stage-chart__swatch" :style="{ background: STAGE_COLORS[i] }" />{{ stage.label }}
        </li>
      </ul>
      <p v-if="rows.length === 0" class="u-text-muted">No building elements in this project.</p>
      <div v-for="bar in bars" :key="bar.element" class="stage-chart__row" aria-hidden="true">
        <span class="stage-chart__label">{{ bar.element }}</span>
        <div class="stage-chart__track">
          <span class="stage-chart__zero" :style="{ left: `${zero}%` }" />
          <span
            v-for="segment in bar.segments"
            :key="segment.key"
            class="stage-chart__segment"
            :style="{ left: `${segment.left}%`, width: `${segment.width}%`, background: segment.color }"
            :title="segment.title"
          />
        </div>
      </div>
      <figcaption class="stage-chart__caption">
        kg CO₂e, same values as the table. Negative values extend left of zero.
      </figcaption>
    </figure>

    <q-table
      flat
      bordered
      hide-bottom
      :rows="rows"
      :columns="columns"
      row-key="element"
      :pagination="{ rowsPerPage: 0 }"
      no-data-label="No building elements in this project"
    />
  </div>
</template>

<script setup lang="ts">
import { STAGE_COLORS } from '@/dataviz';
import { computed } from 'vue';
import type { QTableColumn } from 'quasar';
import type { ElementStages, StageTotal } from '@/api/overview';

const props = defineProps<{ stages: StageTotal[]; rows: ElementStages[] }>();


// The reader's locale; no i18n in the app yet.
const kg = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const percent = new Intl.NumberFormat(undefined, { style: 'percent' });

const columns = computed<QTableColumn<ElementStages>[]>(() => [
  { name: 'element', label: 'Element', field: 'element', align: 'left' },
  ...props.stages.map((stage) => ({
    name: stage.key,
    label: stage.label,
    field: (row: ElementStages) => row.gwp_by_stage[stage.key],
    format: (value: number) => kg.format(value),
    align: 'right' as const,
  })),
  {
    name: 'dominant',
    label: 'Dominant stage',
    field: (row) => `${row.dominant_stage} ${percent.format(row.dominant_share)}`,
    align: 'right',
  },
]);

// Chart geometry only: each bar stacks positive stages right of zero, negative ones left.
const domain = computed(() => {
  const values = props.rows.map((row) => Object.values(row.gwp_by_stage));
  const min = Math.min(0, ...values.map((v) => v.filter((x) => x < 0).reduce((a, b) => a + b, 0)));
  const max = Math.max(0, ...values.map((v) => v.filter((x) => x > 0).reduce((a, b) => a + b, 0)));
  return { min, span: max - min };
});

const toPercent = (value: number) => ((value - domain.value.min) / domain.value.span) * 100;
const zero = computed(() => toPercent(0));

const bars = computed(() =>
  props.rows.map((row) => {
    let positive = 0;
    let negative = 0;
    const segments = props.stages.map((stage, i) => {
      const value = row.gwp_by_stage[stage.key];
      const start = value < 0 ? negative + value : positive;
      if (value < 0) negative += value;
      else positive += value;
      return {
        key: stage.key,
        left: toPercent(start),
        width: (Math.abs(value) / domain.value.span) * 100,
        color: STAGE_COLORS[i],
        title: `${stage.label}: ${kg.format(value)} kg CO₂e`,
      };
    });
    return { element: row.element, segments };
  }),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

// Chart (overview) above table (detail); side by side, the table clips its columns.
.results-view {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}

.stage-chart {
  margin: 0;
  padding: tokens.$spacing-xl;
}

.stage-chart__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-lg;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.stage-chart__legend li {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-xs;
}

.stage-chart__swatch {
  width: tokens.$spacing-md;
  height: tokens.$spacing-md;
  border-radius: tokens.$radius-xs;
}

.stage-chart__row {
  display: grid;
  grid-template-columns: minmax(0, 12rem) minmax(0, 1fr);
  align-items: center;
  gap: tokens.$spacing-md;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.stage-chart__label {
  text-align: right;
}

.stage-chart__track {
  position: relative;
  height: tokens.$size-chip;
}

.stage-chart__zero {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: tokens.$border-width solid tokens.$dataviz-axis-text;
}

.stage-chart__segment {
  position: absolute;
  top: 0;
  bottom: 0;
}

.stage-chart__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

<template>
  <!-- Two buildings, row by row, on one scale around zero: a value below zero (biogenic
       carbon, benefits) runs left of the axis instead of disappearing. -->
  <figure class="paired">
    <table class="paired__table">
      <thead>
        <tr>
          <th scope="col" class="paired__label">{{ unit }}</th>
          <th scope="col" aria-hidden="true" />
          <th scope="col" class="num"><span class="paired__swatch paired__swatch--a" />{{ aLabel }}</th>
          <th scope="col" class="num"><span class="paired__swatch paired__swatch--b" />{{ bLabel }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.label">
          <th scope="row" class="paired__label">{{ row.label }}</th>
          <td class="paired__plot" aria-hidden="true">
            <span class="paired__zero" :style="{ left: `${at(0)}%` }" />
            <span class="paired__bar paired__bar--a" :style="bar(row.a)" />
            <span class="paired__bar paired__bar--b" :style="bar(row.b)" />
          </td>
          <td class="num">{{ show(row.a) }}</td>
          <td class="num">{{ show(row.b) }}</td>
        </tr>
      </tbody>
    </table>
    <figcaption class="paired__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import { kg } from '@/format';

const props = withDefaults(
  defineProps<{
    rows: ComparedRow[];
    aLabel: string;
    bLabel: string;
    unit: string;
    caption: string;
    format?: Intl.NumberFormat;
  }>(),
  { format: () => kg },
);

// Chart geometry only: one domain for every row, zero always inside it.
const domain = computed(() => {
  const values = props.rows.flatMap((r) => [r.a ?? 0, r.b ?? 0]);
  return [Math.min(0, ...values), Math.max(0, ...values)] as const;
});
const at = (value: number) => {
  const [lo, hi] = domain.value;
  return hi === lo ? 0 : ((value - lo) / (hi - lo)) * 100;
};
const bar = (value: number | null) => {
  const v = value ?? 0;
  return { left: `${at(Math.min(0, v))}%`, width: `${Math.abs(at(v) - at(0))}%` };
};
const show = (value: number | null) => (value === null ? 'no area' : props.format.format(value));
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.paired {
  margin: 0;
}

.paired__table {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}

.paired__table th,
.paired__table td {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  vertical-align: middle;
}

.paired__table thead th {
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
  white-space: nowrap;
}

.paired__label {
  width: 30%;
  text-align: left;
  font-weight: tokens.$text-weight-regular;
}

.paired__plot {
  position: relative;
  width: 50%;
  height: 2.25rem;
}

.paired__zero {
  position: absolute;
  top: tokens.$spacing-xxs;
  bottom: tokens.$spacing-xxs;
  border-left: tokens.$border-width solid tokens.$color-text-muted;
}

.paired__bar {
  position: absolute;
  height: 0.6rem;
}

.paired__bar--a {
  top: calc(50% - 0.65rem);
  background: var(--gbdi-dataviz-green-1);
}

.paired__bar--b {
  top: calc(50% + 0.05rem);
  background: var(--gbdi-dataviz-blue-2);
}

.paired__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
  vertical-align: -0.1rem;
}

.paired__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.paired__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
}

.num {
  text-align: right;
  white-space: nowrap;
}

.paired__caption {
  padding-top: tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

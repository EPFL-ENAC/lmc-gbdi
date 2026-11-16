<template>
  <!-- Two buildings, row by row, side by side: each building on its own scale around zero
       (org#94), so no graph mixes the two. A value below zero (biogenic carbon, benefits)
       runs left of its axis instead of disappearing. -->
  <figure class="paired">
    <table class="paired__table">
      <thead>
        <tr>
          <th scope="col" class="paired__label">{{ unit }}</th>
          <template v-for="side in SIDES" :key="side">
            <th scope="col" colspan="2" class="paired__head" :class="`paired__side--${side}`">
              <span class="paired__swatch" :class="`paired__swatch--${side}`" />{{ code(buildings[side]) }}
              <span class="paired__covers">{{ covers(buildings[side]) }}</span>
            </th>
          </template>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.label">
          <th scope="row" class="paired__label"><Term :name="row.label" /></th>
          <template v-for="side in SIDES" :key="side">
            <td class="paired__plot" :class="`paired__side--${side}`" aria-hidden="true">
              <span class="paired__zero" :style="{ left: `${at(side, 0)}%` }" />
              <span class="paired__bar" :class="`paired__bar--${side}`" :style="bar(side, row[side])" />
            </td>
            <td class="num">{{ show(row[side]) }}</td>
          </template>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <th scope="row" class="paired__label">Scale</th>
          <template v-for="side in SIDES" :key="side">
            <td class="paired__ends" :class="`paired__side--${side}`">
              <span>{{ format.format(domains[side][0]) }}</span><span>{{ format.format(domains[side][1]) }}</span>
            </td>
            <td />
          </template>
        </tr>
      </tfoot>
    </table>
    <figcaption class="paired__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { code, type ComparedBuilding, type ComparedRow } from '@/api/buildings';
import Term from '@/components/atoms/Term.vue';
import { kg } from '@/format';

type Side = 'a' | 'b';
const SIDES = ['a', 'b'] as const;

const props = withDefaults(
  defineProps<{
    rows: ComparedRow[];
    a: ComparedBuilding;
    b: ComparedBuilding;
    unit: string;
    caption: string;
    format?: Intl.NumberFormat;
  }>(),
  { format: () => kg },
);

const buildings = computed(() => ({ a: props.a, b: props.b }));
const covers = (x: ComparedBuilding) =>
  `${x.system_boundary ?? 'boundary not declared'} · ${x.lcia_methodology ?? 'method not declared'}`;

// Chart geometry only: one domain per building, from its own values, zero always inside.
const domainOf = (side: Side) => {
  const values = props.rows.map((r) => r[side] ?? 0);
  return [Math.min(0, ...values), Math.max(0, ...values)] as const;
};
const domains = computed(() => ({ a: domainOf('a'), b: domainOf('b') }));
const at = (side: Side, value: number) => {
  const [lo, hi] = domains.value[side];
  return hi === lo ? 0 : ((value - lo) / (hi - lo)) * 100;
};
const bar = (side: Side, value: number | null) => {
  const v = value ?? 0;
  return { left: `${at(side, Math.min(0, v))}%`, width: `${Math.abs(at(side, v) - at(side, 0))}%` };
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
  width: 20%;
  text-align: left;
  font-weight: tokens.$text-weight-regular;
}

.paired__plot {
  position: relative;
  width: 25%;
  height: 2.25rem;
}

// The B part starts after a rule, so the two buildings never read as one graph.
.paired__side--b {
  border-left: tokens.$border-width solid tokens.$color-border;
}

.paired__head {
  text-align: left;
}

.paired__covers {
  display: block;
  font-size: tokens.$text-size-xs;
  white-space: normal;
}

.paired__ends {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.paired__ends span + span {
  float: right;
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
  top: calc(50% - 0.3rem);
  background: var(--gbdi-dataviz-green-1);
}

.paired__bar--b {
  top: calc(50% - 0.3rem);
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

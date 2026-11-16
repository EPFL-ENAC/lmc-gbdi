<template>
  <!-- Two buildings on one axis, row by row: only when the backend says their figures
       cover the same stages (org#94). Otherwise PairedBars keeps each on its own scale. -->
  <figure class="grouped" :aria-label="caption">
    <p class="grouped__legend" aria-hidden="true">
      <span v-for="side in SIDES" :key="side"
        ><span class="grouped__swatch" :class="`grouped__swatch--${side}`" />{{ code(props[side]) }}</span
      >
      <span class="grouped__unit">{{ unit }}</span>
    </p>
    <p v-if="rows.length === 0" class="u-text-muted">Nothing to compare.</p>
    <!-- HTML labels beside the chart, as RankedBars: one band per row, two bars in it. -->
    <div v-else class="grouped__plot">
      <div class="grouped__labels">
        <span v-for="row in rows" :key="row.label" class="grouped__label" :style="{ height: `${ROW}px` }">
          <span class="grouped__name"><Term :name="row.label" /></span>
        </span>
      </div>
      <div role="img" :aria-label="summary" :style="{ minHeight: height }">
        <EChart :option="option" :height="height" />
      </div>
    </div>
    <figcaption class="grouped__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComposeOption } from 'echarts/core';
import type { BarSeriesOption } from 'echarts/charts';
import type { GridComponentOption, TooltipComponentOption } from 'echarts/components';
import { code, type ComparedBuilding, type ComparedRow } from '@/api/buildings';
import Term from '@/components/atoms/Term.vue';
import { asyncEChart, cssColor } from '@/components/atoms/echarts';
import { kg } from '@/format';

const EChart = asyncEChart(() => import('@/components/atoms/echart-bar'));

const SIDES = ['a', 'b'] as const;
// PairedBars' colours: a green, b blue.
const COLOR = { a: 'var(--gbdi-dataviz-green-1)', b: 'var(--gbdi-dataviz-blue-2)' };

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

const ROW = 44; // px per row: two 16 px bars and the gap around them
const height = computed(() => `${props.rows.length * ROW}px`);
const show = (value: number | null) => (value === null ? 'no floor area' : props.format.format(value));

// Outside the chart's chunk, so a screen reader has it before ECharts loads.
const summary = computed(
  () =>
    `${props.caption} ${props.unit}. ` +
    props.rows.map((r) => `${r.label}: ${code(props.a)} ${show(r.a)}, ${code(props.b)} ${show(r.b)}`).join('; '),
);

// Labels come from uploaded workbooks: the tooltip is built as text, never as HTML.
function tip(side: 'a' | 'b', i: number) {
  const row = props.rows[i];
  const box = document.createElement('div');
  if (row) for (const text of [row.label, `${code(props[side])}: ${show(row[side])} ${props.unit}`]) box.appendChild(document.createElement('div')).append(text);
  return box;
}

// One value axis for both, zero included: a negative value runs left of zero, its label
// on the left; a positive one on the right. Each side keeps room for its longest label.
const option = computed((): ComposeOption<BarSeriesOption | GridComponentOption | TooltipComponentOption> => {
  const values = props.rows.flatMap((r) => [r.a ?? 0, r.b ?? 0]);
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const pen = document.createElement('canvas').getContext('2d');
  if (pen) pen.font = `12px ${getComputedStyle(document.body).fontFamily}`;
  const width = (text: string) => pen?.measureText(text).width ?? 7 * text.length;
  const room = (negative: boolean) =>
    8 +
    Math.ceil(
      Math.max(
        0,
        ...props.rows.flatMap((r) => SIDES.map((s) => r[s]).filter((v) => (v ?? 0) < 0 === negative).map((v) => width(show(v)))),
      ),
    );
  return {
    grid: { left: low < 0 ? room(true) : 0, right: room(false), top: 0, bottom: 0 },
    xAxis: { type: 'value', show: false, min: low, max: high || (low ? 0 : 1) },
    yAxis: {
      type: 'category',
      inverse: true,
      data: props.rows.map((r) => r.label),
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: low < 0, onZero: true },
    },
    tooltip: {
      trigger: 'item',
      // As RankedBars: opened on a tap too, and kept in the viewport on a phone.
      extraCssText: 'width: max-content; max-width: calc(100vw - 32px); white-space: normal;',
      position: (point, _params, el, _rect, size) => {
        const left = (el as HTMLElement).parentElement?.getBoundingClientRect().left ?? 0;
        const x = Math.min(point[0] + 12, window.innerWidth - 16 - left - size.contentSize[0]);
        return [Math.max(x, 16 - left), point[1] + 12];
      },
      formatter: (params) => {
        const p = [params].flat()[0];
        return tip(p?.seriesIndex === 1 ? 'b' : 'a', p?.dataIndex ?? 0);
      },
    },
    series: SIDES.map((side) => ({
      type: 'bar',
      barWidth: 16,
      barGap: '10%',
      itemStyle: { color: cssColor(COLOR[side]) },
      data: props.rows.map((r) => ({
        value: r[side] ?? 0,
        label: { position: (r[side] ?? 0) < 0 ? 'left' : 'right' },
      })),
      label: {
        show: true,
        color: cssColor('var(--gbdi-color-text-muted)'),
        formatter: (params) => show(props.rows[params.dataIndex]?.[side] ?? null),
      },
    })),
  };
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.grouped {
  margin: 0 0 tokens.$spacing-xl;
}

.grouped__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-md;
  margin: 0 0 tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  font-weight: tokens.$text-weight-bold;
}

.grouped__unit {
  font-weight: normal;
  color: tokens.$color-text-muted;
}

.grouped__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
  vertical-align: -0.1em;
}

.grouped__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.grouped__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
}

.grouped__plot {
  display: grid;
  // Proportional columns, so the bars keep their length in a narrow card too.
  grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
  gap: tokens.$spacing-md;
}

.grouped__label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  text-align: right;
  font-size: tokens.$text-size-xs;
  line-height: 1.3;
  color: tokens.$color-text-muted;
}

// Two lines fit the row; a longer name is clamped, and stays whole in the tooltip.
.grouped__name {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.grouped__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

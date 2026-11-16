<template>
  <figure class="gbdi-card bars-chart" :aria-label="caption">
    <p v-if="bars.length === 0" class="u-text-muted">{{ emptyLabel }}</p>
    <!-- The labels stay HTML beside the chart: an ECharts axis label cannot hold the
         glossary tooltip of Term. Each label row is as high as its bar's band. -->
    <div v-else class="bars-chart__plot">
      <div class="bars-chart__labels">
        <span v-for="bar in bars" :key="bar.key" class="bars-chart__label" :style="{ height: `${ROW}px` }">
          <span class="bars-chart__name"><Term :name="bar.label" /></span>
        </span>
      </div>
      <div role="img" :aria-label="summary" :style="{ minHeight: height }">
        <EChart :option="option" :height="height" />
      </div>
    </div>
    <figcaption class="bars-chart__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComposeOption } from 'echarts/core';
import type { BarSeriesOption } from 'echarts/charts';
import type { GridComponentOption, TooltipComponentOption } from 'echarts/components';
import Term from '@/components/atoms/Term.vue';
import { asyncEChart, cssColor } from '@/components/atoms/echarts';

const EChart = asyncEChart(() => import('@/components/atoms/echart-bar'));

export interface Bar {
  key: string;
  label: string;
  value: number;
  display: string; // formatted by the page, in the reader's locale
  missing?: boolean; // data the workbook lacks (Not classified, Undeclared): Info orange
}

const props = defineProps<{ bars: Bar[]; caption: string; emptyLabel: string }>();

const ROW = 32; // px per bar: the band of the chart and the height of its HTML label
const height = computed(() => `${props.bars.length * ROW}px`);

// A clamped label stays readable in full here and in the bar's tooltip.
const summary = computed(() => `${props.caption} ${props.bars.map((bar) => `${bar.label}: ${bar.display}`).join('; ')}`);

// Labels come from uploaded workbooks: the tooltip is built as text, never as HTML.
function tip(i: number) {
  const bar = props.bars[i];
  const box = document.createElement('div');
  if (bar) for (const text of [bar.label, bar.display]) box.appendChild(document.createElement('div')).append(text);
  return box;
}

// Chart geometry only: the axis is pinned to the data's own ends, zero included, so the
// longest bar fills the track and a negative value runs left of zero.
const option = computed((): ComposeOption<BarSeriesOption | GridComponentOption | TooltipComponentOption> => {
  const values = props.bars.map((bar) => bar.value);
  const low = Math.min(0, ...values);
  const high = Math.max(0, ...values);
  const fill = cssColor('var(--gbdi-dataviz-1)');
  const missing = cssColor('var(--gbdi-color-severity-info)');
  // Room for the longest value label, measured in the 12 px chart text.
  const pen = document.createElement('canvas').getContext('2d');
  if (pen) pen.font = `12px ${getComputedStyle(document.body).fontFamily}`;
  const gutter = 8 + Math.ceil(Math.max(...props.bars.map((bar) => pen?.measureText(bar.display).width ?? 7 * bar.display.length)));
  return {
    grid: { left: 0, right: gutter, top: 0, bottom: 0 },
    xAxis: { type: 'value', show: false, min: low, max: high || (low ? 0 : 1) },
    // The zero line, drawn only when a bar runs left of it.
    yAxis: {
      type: 'category',
      inverse: true,
      data: props.bars.map((bar) => bar.key),
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: low < 0, onZero: true },
    },
    tooltip: {
      trigger: 'item',
      // The default triggerOn, mousemove|click, also opens it on a tap. The chart column is
      // narrow on a phone, so the tooltip is kept in the viewport, not in the chart.
      extraCssText: 'width: max-content; max-width: calc(100vw - 32px); white-space: normal;',
      position: (point, _params, el, _rect, size) => {
        const left = (el as HTMLElement).parentElement?.getBoundingClientRect().left ?? 0;
        const x = Math.min(point[0] + 12, window.innerWidth - 16 - left - size.contentSize[0]);
        return [Math.max(x, 16 - left), point[1] + 12];
      },
      formatter: (params) => tip([params].flat()[0]?.dataIndex ?? 0),
    },
    series: [
      {
        type: 'bar',
        barWidth: 24,
        data: props.bars.map((bar) => ({ value: bar.value, itemStyle: { color: bar.missing ? missing : fill } })),
        label: {
          show: true,
          position: 'right',
          color: cssColor('var(--gbdi-color-text-muted)'),
          formatter: (params) => props.bars[params.dataIndex]?.display ?? '',
        },
      },
    ],
  };
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.bars-chart {
  margin: 0;
  padding: tokens.$spacing-xl;
}

.bars-chart__plot {
  display: grid;
  // Proportional columns, so the bars keep their length in a narrow card too.
  grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
  gap: tokens.$spacing-md;
}

.bars-chart__label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  text-align: right;
  font-size: tokens.$text-size-xs;
  line-height: 1.3;
  color: tokens.$color-text-muted;
}

// Two lines fit the row; a longer name is clamped, and stays whole in the tooltip.
.bars-chart__name {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
}

.bars-chart__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

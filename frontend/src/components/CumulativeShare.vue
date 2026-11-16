<template>
  <p v-if="!points.length" class="u-text-muted">No material carbon in this project.</p>
  <figure v-else class="cumulative">
    <figcaption class="cumulative__note">{{ headline }}</figcaption>
    <div role="img" :aria-label="summary" :style="{ minHeight: height }">
      <EChart :option="option" :height="height" />
    </div>
  </figure>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, h } from 'vue';
import { useQuasar } from 'quasar';
import type { ComposeOption } from 'echarts/core';
import type { LineSeriesOption } from 'echarts/charts';
import type { GridComponentOption, TooltipComponentOption } from 'echarts/components';
import type { MaterialHotspot } from '@/api/overview';
import { materialName, percent } from '@/format';
import { materialLabel } from '@/materials';

// ECharts loads with the chart only, in its own chunk. The empty state, the
// headline and the summary stay here, outside that chunk.
const EChart = defineAsyncComponent({
  loader: () => import('@/components/atoms/EChart.vue'),
  errorComponent: () => h('p', { class: 'u-text-muted' }, 'The chart failed to load.'),
});

const props = defineProps<{ hotspots: MaterialHotspot[] }>(); // the top 10, by carbon

const $q = useQuasar();
const phone = computed(() => $q.screen.lt.sm);
const height = computed(() => (phone.value ? '280px' : '360px'));

const points = computed(() => {
  let sum = 0;
  return props.hotspots.map((h, i) => ({
    rank: i + 1,
    name: materialName(materialLabel(h)),
    share: h.share,
    value: (sum += h.share),
  }));
});
const n = computed(() => points.value.length);

// Shares can be negative (biogenic carbon), so the scale stretches past 0–100% when it must.
// Multiples of 25%, so 0% is always a tick; a wider step when the scale stretches far.
// The ends snap to a tick, with a tolerance: ten shares can sum to 1.0000000000000002.
const yScale = computed(() => {
  const values = points.value.map((p) => p.value);
  const max = Math.max(1, ...values);
  const min = Math.min(0, ...values);
  const step = 0.25 * Math.max(1, Math.ceil((max - min) / 2));
  return { min: Math.floor(min / step + 1e-9) * step, max: Math.ceil(max / step - 1e-9) * step, interval: step };
});

const last = computed(() => points.value[n.value - 1]?.value ?? 0);
const headline = computed(() => `Top ${n.value} ≈ ${Math.round(last.value * 100)}% of total carbon`);
const summary = computed(
  () =>
    `Cumulative share of carbon over the ${n.value} largest materials: ${headline.value}. ` +
    points.value.map((p) => `${p.rank}. ${p.name}, own share ${percent.format(p.share)}, running share ${percent.format(p.value)}`).join('; '),
);

// Material names come from uploaded workbooks: the tooltip is built with
// textContent, never as HTML.
function tip(rank: number) {
  const p = points.value[rank - 1];
  if (!p) return '';
  const box = document.createElement('div');
  const line = (text: string) => box.appendChild(document.createElement('div')).append(text);
  line(`${p.rank}. ${p.name}`);
  line(`Own share: ${percent.format(p.share)}`);
  line(`Running share: ${percent.format(p.value)}`);
  return box;
}

// Rank 0 is a point at 0% with no dot, so the area starts at the left edge.
const option = computed((): ComposeOption<LineSeriesOption | GridComponentOption | TooltipComponentOption> => ({
  grid: { left: 8, right: 16, top: 16, bottom: 8 },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: [0, ...points.value.map((p) => p.rank)],
    axisTick: { show: false },
    axisLabel: phone.value
      ? { interval: 0, formatter: (rank: string) => (rank === '0' ? '' : rank) }
      : {
          interval: 0,
          rotate: 30,
          width: 140,
          overflow: 'truncate',
          formatter: (rank: string) => points.value[Number(rank) - 1]?.name ?? '',
        },
  },
  yAxis: { type: 'value', ...yScale.value, axisLabel: { formatter: (v: number) => percent.format(v) } },
  tooltip: {
    trigger: 'axis',
    // The default triggerOn, mousemove|click, also opens it on a tap.
    confine: true,
    axisPointer: { type: 'line' },
    formatter: (params) => tip([params].flat()[0]?.dataIndex ?? 0),
  },
  series: [
    {
      type: 'line',
      data: [{ value: 0, symbol: 'none' }, ...points.value.map((p) => p.value)],
      symbol: 'circle',
      symbolSize: 10,
      lineStyle: { width: 2 },
      areaStyle: { opacity: 0.15 },
    },
  ],
}));
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.cumulative {
  margin: 0;
}

.cumulative__note {
  text-align: right;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text;
}
</style>

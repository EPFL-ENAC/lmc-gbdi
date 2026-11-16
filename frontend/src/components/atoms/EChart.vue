<template>
  <div ref="root" class="echart" role="img" :aria-label="ariaLabel" :style="{ height }" />
</template>

<script setup lang="ts">
// One thin wrapper around ECharts, loaded only with a chart (import it with
// defineAsyncComponent). Only the pieces in use() reach the bundle: add a chart
// type or a component there when a chart needs it.
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { init, use, type ECharts, type EChartsCoreOption } from 'echarts/core';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';

use([LineChart, GridComponent, TooltipComponent, SVGRenderer]);

const props = defineProps<{ option: EChartsCoreOption; ariaLabel: string; height: string }>();

const root = ref<HTMLDivElement>();
let chart: ECharts | undefined;
let resize: ResizeObserver | undefined;
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

// ECharts parses and blends colours, so it needs the values, not var(--gbdi-…).
const token = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

// The shared look of every chart, from the app tokens. The root div carries the
// chart font and size (scoped style below), so the theme reads them from it.
function theme(el: HTMLElement) {
  const style = getComputedStyle(el);
  const fontSize = parseFloat(style.fontSize);
  // The tooltip tokens, set in rem on the root below; ECharts takes px.
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
  const tooltipSize = parseFloat(style.getPropertyValue('--echart-tooltip-size')) * rem;
  const axisText = token('--gbdi-dataviz-axis-text');
  const grid = token('--gbdi-dataviz-gridline');
  const axis = {
    axisLine: { lineStyle: { color: grid } },
    axisTick: { lineStyle: { color: grid } },
    axisLabel: { color: axisText, fontSize },
    splitLine: { lineStyle: { color: grid } },
  };
  return {
    // Series colours, in order: the dark step of each hue, as in the SVG charts.
    color: ['green', 'blue', 'purple', 'orange'].map((hue) => token(`--gbdi-dataviz-${hue}-1`)),
    textStyle: { fontFamily: style.fontFamily, fontSize, color: token('--gbdi-color-text') },
    categoryAxis: axis,
    valueAxis: axis,
    tooltip: {
      backgroundColor: token('--gbdi-color-text'),
      borderWidth: 0,
      padding: [style.getPropertyValue('--echart-tooltip-pad-y'), style.getPropertyValue('--echart-tooltip-pad-x')].map((v) => parseFloat(v) * rem),
      textStyle: { color: token('--gbdi-color-text-on-primary'), fontFamily: style.fontFamily, fontSize: tooltipSize },
    },
  };
}

function render() {
  const { option } = props;
  const still = { ...option, animation: false, tooltip: { ...(option.tooltip as object), transitionDuration: 0 } };
  chart?.setOption(reduceMotion.matches ? still : option, true);
}

onMounted(() => {
  const el = root.value!;
  chart = init(el, theme(el), { renderer: 'svg' });
  render();
  resize = new ResizeObserver(() => chart?.resize());
  resize.observe(el);
});

watch(() => props.option, render);
reduceMotion.addEventListener('change', render);

onBeforeUnmount(() => {
  reduceMotion.removeEventListener('change', render);
  resize?.disconnect();
  chart?.dispose();
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.echart {
  width: 100%;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-xs;
  --echart-tooltip-size: #{tokens.$tooltip-font-size};
  --echart-tooltip-pad-y: #{tokens.$tooltip-padding-y};
  --echart-tooltip-pad-x: #{tokens.$tooltip-padding-x};
}
</style>

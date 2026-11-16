<template>
  <!-- The text for screen readers lives on the caller's own element, outside this async
       chunk, so it stays when the chunk is slow or fails to load. -->
  <div ref="root" class="echart" aria-hidden="true" :style="{ height }" />
</template>

<script setup lang="ts">
// One thin wrapper around ECharts, loaded only with a chart (import it with
// asyncEChart from ./echarts). Only the pieces in use() reach the bundle: here the
// renderer and the components every chart shares; each chart registers its own
// series type (echart-line.ts, …).
import { onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { init, use, type ECharts, type EChartsCoreOption } from 'echarts/core';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';

use([GridComponent, TooltipComponent, SVGRenderer]);

const props = defineProps<{ option: EChartsCoreOption; height: string }>();

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
    logAxis: axis,
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
  // A chart without a tooltip must not gain one, so the key is added only where it exists.
  const tooltip = option.tooltip && !Array.isArray(option.tooltip) ? { tooltip: { ...option.tooltip, transitionDuration: 0 } } : {};
  const still = { ...option, animation: false, ...tooltip };
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
  chart = undefined; // a late render must not reach a disposed chart
});

// Linked highlight, for a chart with a table beside it: the item under the pointer in
// series 0 goes out as `hover`, and highlight(i) lights item i from outside (null clears).
const emit = defineEmits<{ hover: [dataIndex: number | null] }>();
onMounted(() => {
  chart?.on('mouseover', { seriesIndex: 0 }, (p) => emit('hover', (p as { dataIndex: number }).dataIndex));
  chart?.on('mouseout', { seriesIndex: 0 }, () => emit('hover', null));
});
let lit: number | null = null;
function highlight(dataIndex: number | null) {
  if (lit !== null) chart?.dispatchAction({ type: 'downplay', seriesIndex: 0, dataIndex: lit });
  if (dataIndex !== null) {
    chart?.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex });
    chart?.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex });
  } else chart?.dispatchAction({ type: 'hideTip' });
  lit = dataIndex;
}
defineExpose({ highlight });
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

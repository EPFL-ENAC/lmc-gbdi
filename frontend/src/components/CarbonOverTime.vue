<template>
  <!-- Whole-life carbon as it accumulates: a step at year 0 (upfront), a slope through
       the years of use, a step at the end of life; module D beyond a dashed boundary. -->
  <figure class="over-time">
    <svg :viewBox="`0 0 ${W} ${H}`" class="over-time__plot" role="img" :aria-label="summary">
      <g class="over-time__grid">
        <line v-for="t in yTicks" :key="`y${t}`" :x1="L" :x2="xEnd" :y1="y(t)" :y2="y(t)" />
      </g>
      <polygon class="over-time__area" :points="areaPoints" />
      <polyline class="over-time__line" :points="linePoints" />
      <line class="over-time__boundary" :x1="xBoundary" :x2="xBoundary" :y1="T" :y2="H - B" />
      <line class="over-time__beyond" :x1="xBeyond" :x2="xBeyond" :y1="y(wholeLife)" :y2="y(wholeLife + moduleD)" />
      <g class="over-time__axis">
        <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">{{ compact.format(t) }}</text>
        <text v-for="year in xTicks" :key="`x${year}`" :x="x(year)" :y="H - B + 18" text-anchor="middle">
          {{ year === 0 ? 'Year 0' : year }}
        </text>
        <text :x="xBeyond" :y="H - B + 18" text-anchor="middle">D</text>
      </g>
      <g class="over-time__note">
        <text :x="x(0) + 10" :y="y(upfront) - 10">Upfront, A1–A5: {{ kg.format(upfront) }} kg</text>
        <text :x="x(period / 2)" :y="y(upfront + useTotal) - 16" text-anchor="middle">
          Use, B1–B8: about {{ kg.format(usePerYear) }} kg a year
        </text>
        <text :x="x(period) - 10" :y="y(wholeLife) - 10" text-anchor="end">
          End of life, C1–C4: {{ kg.format(endOfLife) }} kg
        </text>
        <text :x="xBeyond + 8" :y="y(wholeLife + moduleD / 2) + 4">D1 {{ kg.format(moduleD) }}</text>
      </g>
    </svg>
    <figcaption class="over-time__caption">
      Cumulative kg CO₂e over the {{ period }}-year study period. B1–B8 is spread evenly across the years, a
      simplification: replacements really happen in steps. Dashed: module D, outside the whole-life total.
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { kg } from '@/format';

const props = defineProps<{
  upfront: number;
  useTotal: number; // B1–B8 over the whole study period
  usePerYear: number;
  endOfLife: number;
  wholeLife: number;
  moduleD: number;
  period: number;
}>();

// Drawn at about the size it is shown, so the text keeps its size.
const W = 1100;
const H = 420;
const [L, R, T, B] = [64, 110, 24, 40];
const xEnd = W - R - 48;
const xBoundary = xEnd + 24;
const xBeyond = xEnd + 48;
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });

// Chart geometry only: years along x, cumulative carbon along y, from the backend's totals.
const yMax = computed(() => niceCeiling(props.wholeLife * 1.08));
const x = (year: number) => L + (year / props.period) * (xEnd - L);
const y = (value: number) => H - B - (value / yMax.value) * (H - B - T);
const xTicks = computed(() => Array.from({ length: Math.floor(props.period / 10) + 1 }, (_, i) => i * 10));
const yTicks = computed(() => {
  const step = niceCeiling(yMax.value / 5);
  return Array.from({ length: Math.floor(yMax.value / step) + 1 }, (_, i) => i * step);
});

const corners = computed(() => [
  [x(0), y(0)],
  [x(0), y(props.upfront)],
  [x(props.period), y(props.upfront + props.useTotal)],
  [x(props.period), y(props.wholeLife)],
]);
const linePoints = computed(() => corners.value.map((p) => p.join(',')).join(' '));
const areaPoints = computed(() => [...corners.value, [x(props.period), y(0)]].map((p) => p.join(',')).join(' '));

const summary = computed(
  () =>
    `Carbon over ${props.period} years: ${kg.format(props.upfront)} kg upfront, ` +
    `${kg.format(props.useTotal)} kg in use, ${kg.format(props.endOfLife)} kg at end of life.`,
);

function niceCeiling(value: number) {
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 1.5, 2, 2.5, 5, 10].find((s) => s * magnitude >= value) ?? 10;
  return step * magnitude;
}
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.over-time {
  margin: 0;
}

.over-time__plot {
  display: block;
  width: 100%;
  height: auto;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-xs;
}

.over-time__grid line {
  stroke: tokens.$dataviz-gridline;
}

.over-time__area {
  fill: var(--gbdi-dataviz-green-4);
}

.over-time__line {
  fill: none;
  stroke: tokens.$color-primary-strong;
  stroke-width: 2;
  stroke-linejoin: round;
}

.over-time__boundary {
  stroke: tokens.$color-text-muted;
  stroke-dasharray: 4 4;
}

.over-time__beyond {
  stroke: tokens.$color-text-muted;
  stroke-width: 2;
  stroke-dasharray: 2 3;
}

.over-time__axis text {
  fill: tokens.$dataviz-axis-text;
}

.over-time__note text {
  fill: tokens.$color-text;
  font-size: tokens.$text-size-sm;
}

.over-time__caption {
  max-width: 42rem;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

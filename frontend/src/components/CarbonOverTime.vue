<template>
  <!-- What each moment of the life emits, on one scale (review #81): a peak at year 0
       (A1–A5), a flat band through the years of use (B1–B8, per year), a peak at the
       end of life (C1–C4); beyond a dashed boundary, the D1 credit below the axis. -->
  <figure class="over-time">
    <ul class="over-time__legend">
      <li v-for="(stage, i) in stages" :key="stage.key">
        <span class="over-time__swatch" :style="{ background: STAGE_COLORS[i] }" /><Term :name="stage.label" />
      </li>
      <li><span class="over-time__swatch over-time__swatch--credit" />D1, outside the total</li>
    </ul>
    <svg :viewBox="`0 0 ${W} ${H}`" class="over-time__plot" role="img" :aria-label="summary">
      <g class="over-time__grid">
        <line v-for="t in yTicks" :key="`y${t}`" :x1="L" :x2="xD + BAR" :y1="y(t)" :y2="y(t)" />
      </g>
      <rect
        v-for="part in parts"
        :key="part.key"
        :x="part.x"
        :y="Math.min(y(part.from), y(part.to))"
        :width="part.width"
        :height="Math.max(Math.abs(y(part.to) - y(part.from)), 1)"
        :style="{ fill: part.color }"
      >
        <title>{{ part.title }}</title>
      </rect>
      <rect
        class="over-time__credit"
        :x="xD"
        :y="Math.min(y(0), y(moduleD))"
        :width="BAR"
        :height="Math.abs(y(moduleD) - y(0))"
      >
        <title>D1: {{ kg.format(moduleD) }} kg CO₂e, outside the whole-life total</title>
      </rect>
      <line class="over-time__zero" :x1="L" :x2="xD + BAR" :y1="y(0)" :y2="y(0)" />
      <line class="over-time__boundary" :x1="xBoundary" :x2="xBoundary" :y1="T" :y2="H - B" />
      <g class="over-time__axis">
        <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">{{ compact.format(t || 0) }}</text>
        <text :x="L + BAR / 2" :y="H - B + 18" text-anchor="middle">Year 0</text>
        <text :x="(xUse + xEnd) / 2" :y="H - B + 18" text-anchor="middle">Years 1 to {{ period }}</text>
        <text :x="xEnd + BAR / 2" :y="H - B + 18" text-anchor="middle">Year {{ period }}</text>
        <text :x="xD + BAR / 2" :y="H - B + 18" text-anchor="middle">Beyond</text>
      </g>
      <g class="over-time__note">
        <text :x="L + BAR + 8" :y="y(upfront) + 4">A1–A5: {{ kg.format(upfront) }} kg</text>
        <text :x="(xUse + xEnd) / 2" :y="y(Math.max(usePerYear, 0)) - 10" text-anchor="middle">
          B1–B8: about {{ kg.format(usePerYear) }} kg a year
        </text>
        <text :x="xEnd - 8" :y="y(endOfLife) + 4" text-anchor="end">C1–C4: {{ kg.format(endOfLife) }} kg</text>
        <text :x="xD - 8" :y="y(moduleD) + 4" text-anchor="end">D1: {{ kg.format(moduleD) }} kg</text>
      </g>
    </svg>
    <figcaption class="over-time__caption">
      kg CO₂e each moment emits, on one scale. B1–B8 is spread evenly over the {{ period }} years, a simplification:
      replacements really happen in steps. Below the axis, dashed: module D1, outside the whole-life total.
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { StageTotal } from '@/api/overview';
import Term from '@/components/atoms/Term.vue';
import { STAGE_COLORS } from '@/dataviz';
import { kg } from '@/format';

const props = defineProps<{
  stages: StageTotal[]; // A1–A3, A4–A5, B1–B8, C1–C4, in that order
  usePerYear: number;
  moduleD: number;
  period: number;
}>();

// Drawn at about the size it is shown, so the text keeps its size.
const W = 1100;
const H = 420;
const [L, R, T, B] = [64, 16, 24, 40];
const BAR = 44; // a peak's width: one moment, not a span of years
const xD = W - R - BAR; // the D1 credit, past the boundary
const xBoundary = xD - 140; // room for the D1 label between the boundary and its bar
const xEnd = xBoundary - 24 - BAR; // the end-of-life bar
const xUse = L + BAR; // the years of use run between the two peaks
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });

const gwp = (key: string) => props.stages.find((s) => s.key === key)?.gwp ?? 0;
const color = (key: string) => STAGE_COLORS[props.stages.findIndex((s) => s.key === key)];
const upfront = computed(() => gwp('a1_a3') + gwp('a4_a5'));
const endOfLife = computed(() => gwp('c1_c4'));

// One scale for every part, zero included, so a negative credit or year shows below it.
const yMax = computed(() => niceCeiling(Math.max(upfront.value, endOfLife.value, props.usePerYear, 0) * 1.1));
const yMin = computed(() => -niceCeiling(-Math.min(props.moduleD, props.usePerYear, upfront.value, endOfLife.value, 0) * 1.1));
const y = (value: number) => T + ((yMax.value - value) / (yMax.value - yMin.value)) * (H - B - T);
const yTicks = computed(() => {
  const step = niceCeiling((yMax.value - yMin.value) / 5);
  const ticks = [];
  for (let t = Math.ceil(yMin.value / step) * step; t <= yMax.value; t += step) ticks.push(t);
  return ticks;
});

// Year 0 stacks A1–A3 and A4–A5; the rest are single parts from zero.
const parts = computed(() => {
  const a13 = gwp('a1_a3');
  const a45 = gwp('a4_a5');
  const stacked = Math.sign(a13) === Math.sign(a45) ? a13 : 0; // ponytail: opposite signs both start at zero
  return [
    { key: 'a1_a3', x: L, width: BAR, from: 0, to: a13, title: `A1–A3: ${kg.format(a13)} kg CO₂e` },
    { key: 'a4_a5', x: L, width: BAR, from: stacked, to: stacked + a45, title: `A4–A5: ${kg.format(a45)} kg CO₂e` },
    {
      key: 'b1_b8',
      x: xUse,
      width: xEnd - xUse,
      from: 0,
      to: props.usePerYear,
      title: `B1–B8: about ${kg.format(props.usePerYear)} kg CO₂e a year`,
    },
    { key: 'c1_c4', x: xEnd, width: BAR, from: 0, to: endOfLife.value, title: `C1–C4: ${kg.format(endOfLife.value)} kg CO₂e` },
  ].map((part) => ({ ...part, color: color(part.key) }));
});

const summary = computed(
  () =>
    `What each moment emits over ${props.period} years: ${kg.format(upfront.value)} kg CO₂e at year 0, ` +
    `about ${kg.format(props.usePerYear)} kg a year in use, ${kg.format(endOfLife.value)} kg at the end of life, ` +
    `and a credit of ${kg.format(props.moduleD)} kg beyond it.`,
);

function niceCeiling(value: number) {
  if (value <= 0) return 0;
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

.over-time__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-lg;
  margin: 0 0 tokens.$spacing-sm;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.over-time__legend li {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-xs;
}

.over-time__swatch {
  width: tokens.$spacing-md;
  height: tokens.$spacing-md;
  border-radius: tokens.$radius-xs;
}

.over-time__swatch--credit {
  border: 2px dashed tokens.$color-text-muted;
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

.over-time__zero {
  stroke: tokens.$dataviz-axis-text;
}

.over-time__boundary {
  stroke: tokens.$color-text-muted;
  stroke-dasharray: 4 4;
}

// Outside the total: an outline, never a fill.
.over-time__credit {
  fill: none;
  stroke: tokens.$color-text-muted;
  stroke-width: 2;
  stroke-dasharray: 4 3;
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

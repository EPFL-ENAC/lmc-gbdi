<template>
  <p v-if="!points.length" class="u-text-muted">No material carbon in this project.</p>
  <figure v-else class="cumulative">
    <svg :viewBox="`0 0 ${W} ${H}`" class="cumulative__plot" role="img" :aria-label="summary">
      <g class="cumulative__grid">
        <line v-for="t in yTicks" :key="`y${t}`" :x1="L" :x2="W - R" :y1="y(t)" :y2="y(t)" />
      </g>
      <path class="cumulative__area" :d="area" />
      <polyline class="cumulative__line" :points="line" />
      <circle v-for="p in points" :key="p.rank" class="cumulative__dot" :cx="x(p.rank)" :cy="y(p.value)" r="5">
        <title>{{ p.rank }}. {{ p.name }}: {{ percent.format(p.value) }} cumulative</title>
      </circle>
      <g class="cumulative__axis">
        <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">{{ percent.format(t) }}</text>
        <text :x="x(1)" :y="H - B + 18" text-anchor="middle">1 material</text>
        <text v-if="n > 1" :x="x(n)" :y="H - B + 18" text-anchor="middle">{{ n }}</text>
      </g>
      <text class="cumulative__note" :x="W - R" :y="T - 8" text-anchor="end">{{ headline }}</text>
    </svg>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { MaterialHotspot } from '@/api/overview';
import { percent } from '@/format';

const props = defineProps<{ hotspots: MaterialHotspot[] }>(); // the top 10, by whole-life carbon

const W = 1100;
const H = 360;
const [L, R, T, B] = [64, 24, 32, 40];

const points = computed(() => {
  let sum = 0;
  return props.hotspots.map((h, i) => ({ rank: i + 1, name: h.material || 'Unnamed material', value: (sum += h.share) }));
});
const n = computed(() => points.value.length);

// Shares can be negative (biogenic carbon), so the scale stretches past 0–100% when it must.
const yMax = computed(() => Math.max(1, ...points.value.map((p) => p.value)));
const yMin = computed(() => Math.min(0, ...points.value.map((p) => p.value)));
const yTicks = computed(() => {
  const ticks = [];
  for (let t = Math.ceil(yMin.value / 0.25) * 0.25; t <= yMax.value + 1e-9; t += 0.25) ticks.push(t);
  return ticks;
});
const y = (value: number) => T + ((yMax.value - value) / (yMax.value - yMin.value)) * (H - B - T);
// Rank 0 sits at the left edge, where the area starts from 0%.
const x = (rank: number) => L + (rank / n.value) * (W - L - R);

const line = computed(() => points.value.map((p) => `${x(p.rank)},${y(p.value)}`).join(' '));
const area = computed(() => `M${x(0)},${y(0)} L${line.value} L${x(n.value)},${y(0)} Z`);

const last = computed(() => points.value[n.value - 1]?.value ?? 0);
const headline = computed(() => `Top ${n.value} ≈ ${Math.round(last.value * 100)}% of whole-life`);
const summary = computed(
  () => `Cumulative share of whole-life carbon over the ${n.value} largest materials: ${headline.value}.`,
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.cumulative {
  margin: 0;
}

.cumulative__plot {
  display: block;
  width: 100%;
  height: auto;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-xs;
}

.cumulative__grid line {
  stroke: tokens.$dataviz-gridline;
}

.cumulative__area {
  fill: var(--gbdi-dataviz-green-1);
  fill-opacity: 0.15;
}

.cumulative__line {
  fill: none;
  stroke: var(--gbdi-dataviz-green-1);
  stroke-width: 2;
}

.cumulative__dot {
  fill: var(--gbdi-dataviz-green-1);
}

.cumulative__axis text {
  fill: tokens.$dataviz-axis-text;
}

.cumulative__note {
  fill: tokens.$color-text;
  font-size: tokens.$text-size-sm;
}
</style>

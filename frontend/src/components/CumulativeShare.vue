<template>
  <p v-if="!points.length" class="u-text-muted">No material carbon in this project.</p>
  <figure v-else class="cumulative">
    <svg :viewBox="`0 0 ${W} ${H}`" class="cumulative__plot" role="group" :aria-label="summary">
      <g class="cumulative__grid">
        <line v-for="t in yTicks" :key="`y${t}`" :x1="L" :x2="W - R" :y1="y(t)" :y2="y(t)" />
      </g>
      <path class="cumulative__area" :d="area" />
      <polyline class="cumulative__line" :points="line" />
      <!-- A dot is small: a wider, unseen circle takes the pointer, the finger and the focus. -->
      <line v-if="active" class="cumulative__guide" :x1="x(active.rank)" :x2="x(active.rank)" :y1="y(active.value)" :y2="H - B" />
      <g
        v-for="p in points"
        :key="p.rank"
        class="cumulative__point"
        :class="{ 'cumulative__point--active': active === p }"
        tabindex="0"
        role="img"
        :aria-label="tipText(p)"
        @pointerenter="activeRank = p.rank"
        @pointerleave="(e: PointerEvent) => e.pointerType !== 'touch' && (activeRank = null)"
        @focus="activeRank = p.rank"
        @blur="activeRank = null"
        @keydown.esc="activeRank = null"
      >
        <circle class="cumulative__hit" :cx="x(p.rank)" :cy="y(p.value)" r="18" />
        <circle class="cumulative__dot" :cx="x(p.rank)" :cy="y(p.value)" r="5" />
      </g>
      <g class="cumulative__axis">
        <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">{{ percent.format(t) }}</text>
        <text :x="x(1)" :y="H - B + 18" :text-anchor="n === 1 ? 'end' : 'middle'">1 material</text>
        <text v-if="n > 1" :x="x(n)" :y="H - B + 18" text-anchor="middle">{{ n }}</text>
      </g>
      <text class="cumulative__note" :x="W - R" :y="T - 8" text-anchor="end">{{ headline }}</text>
    </svg>
    <!-- The tooltip is HTML over the plot: it opens on hover, on a tap and on keyboard
         focus, which a native SVG title does not. The summary above holds the same
         figures for a screen reader. -->
    <div
      v-if="active"
      class="cumulative__tip"
      :class="[`cumulative__tip--${tipSide}`, { 'cumulative__tip--below': tipBelow }]"
      :style="{ left: `${(x(active.rank) / W) * 100}%`, top: `${(y(active.value) / H) * 100}%` }"
      aria-hidden="true"
    >
      <strong>{{ active.rank }}. {{ active.name }}</strong>
      <span>{{ percent.format(active.share) }} of the carbon</span>
      <span v-if="active.rank > 1">{{ percent.format(active.value) }} with the {{ active.rank - 1 }} larger</span>
    </div>
  </figure>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { MaterialHotspot } from '@/api/overview';
import { materialName, percent } from '@/format';
import { materialLabel } from '@/materials';

const props = defineProps<{ hotspots: MaterialHotspot[] }>(); // the top 10, by carbon

const W = 1100;
const H = 360;
const [L, R, T, B] = [64, 24, 32, 40];

const points = computed(() => {
  let sum = 0;
  return props.hotspots.map((h, i) => ({ rank: i + 1, name: materialName(materialLabel(h)), share: h.share, value: (sum += h.share) }));
});
const n = computed(() => points.value.length);

// The point under the pointer, the finger or the keyboard focus.
// Held as a rank, so a new naming or basis shows the new figures and never a stale point.
const activeRank = ref<number | null>(null);
const active = computed(() => (activeRank.value === null ? null : (points.value[activeRank.value - 1] ?? null)));
type Point = (typeof points.value)[number];
const tipText = (p: Point) =>
  `${p.rank}. ${p.name}: ${percent.format(p.share)} of the carbon` +
  (p.rank > 1 ? `, ${percent.format(p.value)} with the ${p.rank - 1} larger` : '');
// A dot near the top of the plot opens its tooltip below, clear of the headline.
const tipBelow = computed(() => (active.value ? y(active.value.value) / H < 0.4 : false));
// The tooltip opens toward the middle of the plot, so the first and last stay inside it.
const tipSide = computed(() => {
  const at = active.value ? active.value.rank / n.value : 0.5;
  return at > 0.6 ? 'left' : at < 0.4 ? 'right' : 'center';
});

// Shares can be negative (biogenic carbon), so the scale stretches past 0–100% when it must.
const yMax = computed(() => Math.max(1, ...points.value.map((p) => p.value)));
const yMin = computed(() => Math.min(0, ...points.value.map((p) => p.value)));
const yTicks = computed(() => {
  // Multiples of 25%, so 0% is always a tick; a wider step when the scale stretches far.
  const step = 0.25 * Math.max(1, Math.ceil((yMax.value - yMin.value) / 2));
  const ticks = [];
  for (let t = Math.ceil(yMin.value / step) * step; t <= yMax.value; t += step) ticks.push(t || 0);
  return ticks;
});
const y = (value: number) => T + ((yMax.value - value) / (yMax.value - yMin.value)) * (H - B - T);
// Rank 0 sits at the left edge, where the area starts from 0%.
const x = (rank: number) => L + (rank / n.value) * (W - L - R);

const line = computed(() => points.value.map((p) => `${x(p.rank)},${y(p.value)}`).join(' '));
const area = computed(() => `M${x(0)},${y(0)} L${line.value} L${x(n.value)},${y(0)} Z`);

const last = computed(() => points.value[n.value - 1]?.value ?? 0);
const headline = computed(() => `Top ${n.value} ≈ ${Math.round(last.value * 100)}% of total carbon`);
const summary = computed(
  () =>
    `Cumulative share of carbon over the ${n.value} largest materials: ${headline.value}. ` +
    points.value.map((p) => `${p.rank}. ${p.name}, ${percent.format(p.value)}`).join('; '),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.cumulative {
  position: relative;
  margin: 0;
}

.cumulative__tip {
  position: absolute;
  z-index: 1;
  display: flex;
  flex-direction: column;
  width: max-content;
  max-width: 12rem;
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-xs;
  background: tokens.$color-surface;
  color: tokens.$color-text;
  font-size: tokens.$text-size-xs;
  pointer-events: none;
  transform: translate(-50%, calc(-100% - #{tokens.$spacing-md}));
}

.cumulative__tip--left {
  transform: translate(-100%, calc(-100% - #{tokens.$spacing-md}));
}

.cumulative__tip--right {
  transform: translate(0, calc(-100% - #{tokens.$spacing-md}));
}

.cumulative__tip--below {
  transform: translate(-50%, tokens.$spacing-md);
}

.cumulative__tip--below.cumulative__tip--left {
  transform: translate(-100%, tokens.$spacing-md);
}

.cumulative__tip--below.cumulative__tip--right {
  transform: translate(0, tokens.$spacing-md);
}

.cumulative__guide {
  stroke: tokens.$dataviz-axis-text;
  stroke-dasharray: 3 3;
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

.cumulative__hit {
  fill: transparent;
}

.cumulative__point {
  cursor: help;
  outline: none; // the ring below replaces it: an outline on an SVG group draws a box
}

.cumulative__point:focus-visible .cumulative__hit {
  stroke: tokens.$color-text;
  stroke-width: 2;
}

.cumulative__point--active .cumulative__dot {
  stroke: var(--gbdi-dataviz-green-1);
  stroke-width: 6;
  stroke-opacity: 0.3;
}

.cumulative__axis text {
  fill: tokens.$dataviz-axis-text;
}

.cumulative__note {
  fill: tokens.$color-text;
  font-size: tokens.$text-size-sm;
}
</style>

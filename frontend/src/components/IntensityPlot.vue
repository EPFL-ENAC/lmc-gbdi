<template>
  <!-- Mass against carbon, both on log scales: the diagonals are lines of equal carbon
       per kg, so a heavy, low-intensity material and a light, intense one read apart. -->
  <figure class="intensity">
    <svg :viewBox="`0 0 ${W} ${H}`" class="intensity__plot" role="img" :aria-label="summary">
      <defs>
        <clipPath :id="clipId"><rect :x="L" :y="T" :width="W - L - R" :height="H - T - B" /></clipPath>
      </defs>
      <g class="intensity__grid">
        <line v-for="t in xTicks" :key="`x${t}`" :x1="x(t)" :x2="x(t)" :y1="T" :y2="H - B" />
        <line v-for="t in yTicks" :key="`y${t}`" :x1="L" :x2="W - R" :y1="y(t)" :y2="y(t)" />
      </g>
      <g class="intensity__iso" :clip-path="`url(#${clipId})`">
        <line v-for="iso in isoLines" :key="iso.k" :x1="iso.x1" :y1="iso.y1" :x2="iso.x2" :y2="iso.y2" />
      </g>
      <g class="intensity__iso-label">
        <text v-for="iso in isoLines" :key="iso.k" :x="iso.x2 - 4" :y="iso.y2 + 14" text-anchor="end">
          {{ iso.k }} {{ units.intensity }}
        </text>
      </g>
      <g class="intensity__axis">
        <text v-for="t in xTicks" :key="`xl${t}`" :x="x(t)" :y="H - B + 16" text-anchor="middle">
          {{ compact.format(t) }}
        </text>
        <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">
          {{ compact.format(t) }}
        </text>
        <text :x="W - R" :y="H - 4" text-anchor="end">Mass ({{ units.mass }})</text>
        <text :x="L" :y="T - 4">GWP ({{ units.carbon }})</text>
      </g>
      <g v-for="p in points" :key="p.key" class="intensity__point">
        <title>{{ p.rank }}. {{ p.name }}</title>
        <circle :cx="p.cx" :cy="p.cy" r="9" />
        <text :x="p.cx" :y="p.cy + 4" text-anchor="middle">{{ p.rank }}</text>
      </g>
    </svg>
    <!-- The legend (#87): what a dot and a dashed line stand for, then the numbers'
         names, as the material cards rank them. -->
    <figcaption class="intensity__caption">
      <ul class="intensity__keys">
        <li>
          <svg viewBox="0 0 16 16" class="intensity__key" aria-hidden="true"><circle cx="8" cy="8" r="7" /></svg>
          One material, at its mass and its whole-life carbon. The number is its rank by carbon.
        </li>
        <li>
          <svg viewBox="0 0 24 16" class="intensity__key intensity__key--iso" aria-hidden="true">
            <line x1="0" y1="14" x2="24" y2="2" />
          </svg>
          Equal carbon per kg, in {{ units.intensity }}: a material above a line is more carbon intense.
        </li>
      </ul>
      <ol class="intensity__names">
        <li v-for="p in points" :key="p.key" :value="p.rank">{{ p.name }}</li>
      </ol>
      <p>{{ caption }}</p>
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';
import type { MaterialHotspot, Units } from '@/api/overview';
import { kg } from '@/format';
import { materialLabel, pairKey } from '@/materials';

const props = defineProps<{ hotspots: MaterialHotspot[]; units: Units }>();

const W = 640;
const H = 420;
const [L, R, T, B] = [56, 24, 24, 40];
const ISO = [0.01, 0.1, 1, 10];
const clipId = `intensity-${useId()}`;
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });

// Plot geometry only: log10 positions within powers-of-ten bounds.
const ranks = computed(() => props.hotspots.map((h, i) => ({ ...h, rank: i + 1 })));
const plotted = computed(() => ranks.value.filter((h) => h.mass_kg > 0 && h.gwp > 0));
const bounds = (values: number[]) => [
  10 ** Math.floor(Math.log10(Math.min(...values))),
  10 ** Math.ceil(Math.log10(Math.max(...values))),
];
const xDomain = computed(() => bounds(plotted.value.map((h) => h.mass_kg)));
const yDomain = computed(() => bounds(plotted.value.map((h) => h.gwp)));
const scale = (v: number, [lo, hi]: number[], from: number, to: number) =>
  from + ((Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo))) * (to - from);
const x = (v: number) => scale(v, xDomain.value, L, W - R);
const y = (v: number) => scale(v, yDomain.value, H - B, T);
const powers = ([lo, hi]: number[]) =>
  Array.from({ length: Math.round(Math.log10(hi / lo)) + 1 }, (_, i) => lo * 10 ** i);
const xTicks = computed(() => powers(xDomain.value));
const yTicks = computed(() => powers(yDomain.value));

// GWP = k × mass is a straight diagonal in log-log; it ends where it leaves the plot.
const isoLines = computed(() => {
  const [xLo, xHi] = xDomain.value;
  const [yLo, yHi] = yDomain.value;
  return ISO.map((k) => {
    const start = Math.max(xLo, yLo / k);
    const end = Math.min(xHi, yHi / k);
    return { k, x1: x(start), y1: y(k * start), x2: x(end), y2: y(k * end), visible: start < end };
  }).filter((line) => line.visible);
});

const points = computed(() =>
  plotted.value.map((h) => ({
    key: pairKey(h),
    name: materialLabel(h),
    rank: h.rank, // the dot shows its rank: names collided, numbers do not
    cx: x(h.mass_kg),
    cy: y(h.gwp),
  })),
);

const skipped = computed(() => props.hotspots.length - plotted.value.length);
const summary = computed(
  () => `${plotted.value.length} materials by mass and whole-life carbon; the same values are in the material tables.`,
);
const caption = computed(
  () =>
    `The top ${props.hotspots.length} materials by whole-life carbon.` +
    (skipped.value > 0 ? ` ${kg.format(skipped.value)} without a declared mass are not plotted.` : ''),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.intensity {
  margin: 0;
}

.intensity__plot {
  display: block;
  width: 100%;
  height: auto;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-xs;
}

.intensity__grid line {
  stroke: tokens.$dataviz-gridline;
}

.intensity__iso line {
  stroke: tokens.$illustration-stroke;
  stroke-width: tokens.$illustration-stroke-width;
  stroke-dasharray: 4 4;
}

.intensity__iso-label text,
.intensity__axis text {
  fill: tokens.$dataviz-axis-text;
}

.intensity__point circle,
.intensity__key circle {
  fill: tokens.$color-primary-strong; // white rank numbers on it stay legible
}

.intensity__point text {
  fill: tokens.$color-text-on-primary;
  font-weight: tokens.$text-weight-bold;
}

.intensity__key--iso line {
  stroke: tokens.$illustration-stroke;
  stroke-width: tokens.$illustration-stroke-width;
  stroke-dasharray: 4 4;
}

.intensity__caption {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.intensity__caption p {
  margin: 0;
}

.intensity__keys {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-xs tokens.$spacing-xl;
  margin: 0;
  padding: 0;
  list-style: none;
}

.intensity__keys li {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
}

.intensity__key {
  flex: none;
  width: tokens.$spacing-lg;
  height: tokens.$spacing-md;
}

.intensity__names {
  columns: 2 14rem;
  margin: 0;
  padding-left: tokens.$spacing-xl;
  color: tokens.$color-text;
}
</style>

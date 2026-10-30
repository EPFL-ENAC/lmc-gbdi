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
          {{ iso.k }} kg CO₂e/kg
        </text>
      </g>
      <g class="intensity__axis">
        <text v-for="t in xTicks" :key="`xl${t}`" :x="x(t)" :y="H - B + 16" text-anchor="middle">
          {{ compact.format(t) }}
        </text>
        <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">
          {{ compact.format(t) }}
        </text>
        <text :x="W - R" :y="H - 4" text-anchor="end">Mass (kg)</text>
        <text :x="L" :y="T - 4">GWP (kg CO₂e)</text>
      </g>
      <g v-for="p in points" :key="p.key" class="intensity__point">
        <title>{{ p.name }}</title>
        <circle :cx="p.cx" :cy="p.cy" r="5" />
        <text :x="p.flip ? p.cx - 9 : p.cx + 9" :y="p.cy + 4" :text-anchor="p.flip ? 'end' : 'start'">
          {{ p.label }}
        </text>
      </g>
    </svg>
    <figcaption class="intensity__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue';
import type { MaterialHotspot } from '@/api/overview';
import { kg } from '@/format';

const props = defineProps<{ hotspots: MaterialHotspot[] }>();

const W = 640;
const H = 420;
const [L, R, T, B] = [56, 24, 24, 40];
const ISO = [0.01, 0.1, 1, 10];
const clipId = `intensity-${useId()}`;
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });

// Plot geometry only: log10 positions within powers-of-ten bounds.
const plotted = computed(() => props.hotspots.filter((h) => h.mass_kg > 0 && h.gwp > 0));
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
  plotted.value.map((h) => {
    const name = h.material || h.epd_product;
    const cx = x(h.mass_kg);
    return {
      key: `${h.material}|${h.epd_product}`,
      name,
      // Long EPD names are cut; the full name is the point's tooltip.
      label: name.length > 24 ? `${name.slice(0, 23)}…` : name,
      cx,
      cy: y(h.gwp),
      flip: cx > W * 0.7, // labels near the right edge read leftwards
    };
  }),
);

const skipped = computed(() => props.hotspots.length - plotted.value.length);
const summary = computed(
  () => `${plotted.value.length} materials by mass and whole-life carbon; the same values are in the hotspot table.`,
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

.intensity__point circle {
  fill: tokens.$color-primary;
}

.intensity__point text {
  fill: tokens.$color-text;
}

.intensity__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

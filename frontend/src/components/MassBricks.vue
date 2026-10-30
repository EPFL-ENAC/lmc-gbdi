<template>
  <!-- The building's mass as a wall of 100 bricks, each one per cent of the mass:
       the four heaviest materials in the categorical colours, the rest in Green-Grey. -->
  <figure class="bricks" :aria-label="`Mass by material, ${kg.format(totalMass)} kg in total`">
    <div class="bricks__wall" aria-hidden="true">
      <span v-for="(brick, i) in wall" :key="i" class="bricks__brick" :style="{ background: brick }" />
    </div>
    <ul class="bricks__legend">
      <li v-for="(item, i) in named" :key="item.key">
        <span class="bricks__swatch" :style="{ background: COLORS[i] }" />
        <span class="bricks__name">{{ item.label }}</span>
        <span class="bricks__value">{{ kg.format(item.mass_kg) }} kg, {{ percent.format(item.share_of_mass) }}</span>
      </li>
      <li>
        <span class="bricks__swatch bricks__swatch--rest" />
        <span class="bricks__name">Every other material</span>
      </li>
    </ul>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { MassHotspot } from '@/api/overview';
import { kg, percent } from '@/format';

const props = defineProps<{ hotspots: MassHotspot[]; totalMass: number }>();

const COLORS = ['var(--gbdi-dataviz-1)', 'var(--gbdi-dataviz-2)', 'var(--gbdi-dataviz-3)', 'var(--gbdi-dataviz-4)'];
const REST = 'var(--gbdi-color-surface-highlight)';

const named = computed(() =>
  props.hotspots.slice(0, COLORS.length).map((h) => ({ ...h, key: `${h.material}|${h.epd_product}`, label: h.material || h.epd_product })),
);

// Drawing geometry only: whole bricks per material by largest remainder, so the
// named bricks add up to their rounded share and the rest fills the wall.
const wall = computed(() => {
  const exact = named.value.map((h) => h.share_of_mass * 100);
  const counts = exact.map(Math.floor);
  const order = exact.map((v, i) => [v - Math.floor(v), i]).sort((a, b) => b[0] - a[0]);
  const target = Math.round(exact.reduce((a, b) => a + b, 0));
  for (let k = 0; counts.reduce((a, b) => a + b, 0) < target; k++) counts[order[k][1]] += 1;
  const bricks = counts.flatMap((n, i) => Array<string>(n).fill(COLORS[i]));
  return [...bricks, ...Array<string>(100 - bricks.length).fill(REST)];
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.bricks {
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: tokens.$spacing-xl;
  align-items: start;
}

// Stacked bond: ten courses of ten bricks, twice as long as they are high.
.bricks__wall {
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: tokens.$spacing-xs;
}

.bricks__brick {
  aspect-ratio: 2 / 1;
  border-radius: tokens.$radius-xs;
}

.bricks__legend {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
  margin: 0;
  padding: 0;
  list-style: none;
}

.bricks__legend li {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  column-gap: tokens.$spacing-sm;
  align-items: center;
}

.bricks__swatch {
  width: tokens.$spacing-lg;
  height: tokens.$spacing-sm;
  border-radius: tokens.$radius-xs;
}

.bricks__swatch--rest {
  background: tokens.$color-surface-highlight;
}

.bricks__value {
  grid-column: 2;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 809px) {
  .bricks {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>

<template>
  <!-- A wall of 100 bricks, each one per cent of the total (mass, or carbon): the four
       largest materials in the categorical colours, the rest in Green-Grey. -->
  <figure class="bricks" :aria-label="`${caption}, ${kg.format(total)} ${unit} in total`">
    <div class="bricks__wall" aria-hidden="true">
      <span v-for="(brick, i) in wall" :key="i" class="bricks__brick" :style="{ background: brick }" />
    </div>
    <ul class="bricks__legend">
      <li v-for="(item, i) in named" :key="item.key">
        <span class="bricks__swatch" :style="{ background: COLORS[i] }" />
        <span class="bricks__name">{{ item.label }}</span>
        <span class="bricks__value">{{ kg.format(item.value) }} {{ unit }}, {{ percent.format(item.share) }}</span>
      </li>
      <li>
        <span class="bricks__swatch bricks__swatch--rest" />
        <span class="bricks__name">Every other material</span>
      </li>
    </ul>
    <figcaption class="bricks__caption">{{ caption }}. One brick is one per cent of {{ kg.format(total) }} {{ unit }}.</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { kg, percent } from '@/format';

export interface Brick {
  key: string;
  label: string;
  value: number; // in `unit`
  share: number; // of `total`, 0–1
}

// `items` largest first; only the first four are named.
const props = defineProps<{ items: Brick[]; total: number; unit: string; caption: string }>();

const COLORS = ['var(--gbdi-dataviz-1)', 'var(--gbdi-dataviz-2)', 'var(--gbdi-dataviz-3)', 'var(--gbdi-dataviz-4)'];
const REST = 'var(--gbdi-color-surface-highlight)';

const named = computed(() => props.items.slice(0, COLORS.length));

// Drawing geometry only: whole bricks per material by largest remainder, so the
// named bricks add up to their rounded share and the rest fills the wall.
const wall = computed(() => {
  // ponytail: shares above 100 % in all (other materials store carbon) cap at the wall.
  const exact = named.value.map((h) => Math.max(h.share, 0) * 100);
  const counts = exact.map(Math.floor);
  const order = exact.map((v, i) => [v - Math.floor(v), i]).sort((a, b) => b[0] - a[0]);
  const target = Math.round(exact.reduce((a, b) => a + b, 0));
  for (let k = 0; counts.reduce((a, b) => a + b, 0) < target; k++) counts[order[k][1]] += 1;
  const bricks = counts.flatMap((n, i) => Array<string>(n).fill(COLORS[i])).slice(0, 100);
  return [...bricks, ...Array<string>(100 - bricks.length).fill(REST)];
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.bricks {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
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

.bricks__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

<template>
  <!-- 100 bricks, each one per cent of the total, laid in the order of `parts`; what
       no part claims is Green-Grey, every other material. -->
  <div class="wall" role="img" :aria-label="label">
    <span v-for="(color, i) in bricks" :key="i" class="wall__brick" :style="{ background: color }" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { OTHER_COLOR } from '@/dataviz';

export interface WallPart {
  color: string;
  share: number; // of the total, 0–1
}

const props = defineProps<{ parts: WallPart[]; label: string }>();

// Drawing geometry only: whole bricks by largest remainder, so the parts add up to
// their rounded share. A negative share (stored carbon) lays no brick, and shares
// over 100 % in all (other materials store carbon) stop at the wall's end.
const bricks = computed(() => {
  const exact = props.parts.map((p) => Math.max(p.share, 0) * 100);
  const counts = exact.map(Math.floor);
  const order = exact.map((v, i) => [v - Math.floor(v), i]).sort((a, b) => b[0] - a[0]);
  const target = Math.min(100, Math.round(exact.reduce((a, b) => a + b, 0)));
  for (let k = 0; counts.reduce((a, b) => a + b, 0) < target; k++) counts[order[k][1]] += 1;
  const laid = counts.flatMap((n, i) => Array<string>(n).fill(props.parts[i].color)).slice(0, 100);
  return [...laid, ...Array<string>(100 - laid.length).fill(OTHER_COLOR)];
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

// Stacked bond: ten courses of ten bricks, twice as long as they are high.
.wall {
  display: grid;
  grid-template-columns: repeat(10, minmax(0, 1fr));
  gap: tokens.$spacing-xs;
}

.wall__brick {
  aspect-ratio: 2 / 1;
  border-radius: tokens.$radius-xs;
}
</style>

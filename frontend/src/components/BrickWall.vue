<template>
  <!-- 100 bricks, each one per cent of the total, laid from the bottom course up in the
       order of `parts`; what no part claims is Green-Grey, every other material. A hover
       or a tap on a brick names its material and lights every brick of that material. -->
  <div class="wall" role="img" :aria-label="label" @pointerleave="active = null">
    <span
      v-for="(brick, i) in bricks"
      :key="i"
      class="wall__brick"
      :class="{ 'wall__brick--dim': active !== null && bricks[active]!.part !== brick.part }"
      :style="{ background: brick.color, gridRow: 10 - Math.floor(i / 10), gridColumn: (i % 10) + 1 }"
      @pointerenter="active = i"
      @click="active = i"
    />
    <!-- The tooltip sits over the hovered brick, in its row and column of the grid. -->
    <div
      v-if="tip"
      class="wall__tip"
      :class="`wall__tip--${tip.side}`"
      :style="{ gridRow: tip.row, gridColumn: tip.column }"
      aria-hidden="true"
    >
      <span>
        <strong>{{ tip.label }}</strong>
        {{ tip.detail }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { OTHER_COLOR } from '@/dataviz';
import { percent } from '@/format';

export interface WallPart {
  color: string;
  label: string; // the material, named on hover
  share: number; // of the total, 0–1
}

const props = defineProps<{ parts: WallPart[]; label: string }>();
// `part` is the index of the material in `parts`, or -1 for every other material.
type Brick = { color: string; part: number; label: string; detail: string };

// Drawing geometry only: whole bricks by largest remainder, so the parts add up to
// their rounded share. A negative share (stored carbon) lays no brick, and shares
// over 100 % in all (other materials store carbon) stop at the wall's end.
const bricks = computed(() => {
  const exact = props.parts.map((p) => Math.max(p.share, 0) * 100);
  const counts = exact.map(Math.floor);
  const order = exact.map((v, i) => [v - Math.floor(v), i]).sort((a, b) => b[0] - a[0]);
  const target = Math.min(100, Math.round(exact.reduce((a, b) => a + b, 0)));
  for (let k = 0; counts.reduce((a, b) => a + b, 0) < target; k++) counts[order[k][1]] += 1;
  const laid = props.parts
    .flatMap((p, i) =>
      Array<Brick>(counts[i]!).fill({ color: p.color, part: i, label: p.label, detail: `${percent.format(p.share)} of the total` }),
    )
    .slice(0, 100);
  const rest = 100 - laid.length;
  const other: Brick = { color: OTHER_COLOR, part: -1, label: 'Every other material', detail: `${rest} of the 100 bricks` };
  return [...laid, ...Array<Brick>(rest).fill(other)];
});

// The brick under the pointer or the finger. Its tooltip opens toward the middle of the
// wall, so it stays inside it at the left and right edges.
const active = ref<number | null>(null);
const tip = computed(() => {
  const brick = active.value === null ? undefined : bricks.value[active.value];
  if (!brick || active.value === null) return null;
  const column = (active.value % 10) + 1;
  return {
    label: brick.label,
    detail: brick.detail,
    row: 10 - Math.floor(active.value / 10),
    column,
    side: column <= 3 ? 'right' : column >= 8 ? 'left' : 'center',
  };
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
  transition: opacity 0.12s;
}

.wall__brick--dim {
  opacity: 0.3;
}

@media (prefers-reduced-motion: reduce) {
  .wall__brick {
    transition: none;
  }
}

// An empty cell over the hovered brick: the bubble hangs above it and takes no pointer,
// so the brick below keeps the hover.
.wall__tip {
  position: relative;
  z-index: 1;
  pointer-events: none;
}

.wall__tip span {
  position: absolute;
  bottom: calc(100% + #{tokens.$spacing-xs});
  left: 50%;
  display: flex;
  flex-direction: column;
  width: max-content;
  max-width: 14rem;
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-xs;
  background: tokens.$color-surface;
  color: tokens.$color-text;
  font-size: tokens.$text-size-xs;
  transform: translateX(-50%);
}

.wall__tip--right span {
  left: 0;
  transform: none;
}

.wall__tip--left span {
  right: 0;
  left: auto;
  transform: none;
}
</style>

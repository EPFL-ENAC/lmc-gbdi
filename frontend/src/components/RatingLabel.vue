<template>
  <!-- A rating scale in the vernacular of the building energy label: one arrow per band,
       longer as the band worsens; only the project's band is filled, in Green Dark. -->
  <figure class="rating" :aria-label="`${benchmark.name}: ${benchmark.band ?? 'not placed'}`">
    <ol class="rating__bands">
      <li
        v-for="(band, i) in benchmark.bands"
        :key="band.label"
        class="rating__band"
        :class="{ 'rating__band--here': band.label === benchmark.band }"
      >
        <span class="rating__bar" :style="{ width: `${36 + (i * 64) / (benchmark.bands.length - 1)}%` }">
          <span class="rating__label">{{ band.label }}</span>
          <span class="rating__range">{{ range(i) }}</span>
        </span>
        <span v-if="band.label === benchmark.band && benchmark.value !== null" class="rating__marker">
          {{ one.format(benchmark.value) }} kg CO₂e/m²
        </span>
      </li>
    </ol>
  </figure>
</template>

<script setup lang="ts">
import type { Benchmark } from '@/api/overview';
import { kg, one } from '@/format';

const props = defineProps<{ benchmark: Benchmark }>();

const range = (i: number) => {
  const { upper } = props.benchmark.bands[i];
  const lower = i === 0 ? null : props.benchmark.bands[i - 1].upper;
  if (lower === null) return `under ${kg.format(upper ?? 0)}`;
  if (upper === null) return `${kg.format(lower)} and over`;
  return `${kg.format(lower)} to ${kg.format(upper)}`;
};
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.rating {
  margin: 0;
}

.rating__bands {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-xs;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rating__band {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-md;
}

// The energy-label arrow: a bar whose right end is a point.
.rating__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: tokens.$spacing-md;
  min-height: tokens.$size-chip;
  padding: tokens.$spacing-xxs tokens.$spacing-xl tokens.$spacing-xxs tokens.$spacing-md;
  background: tokens.$color-surface-highlight;
  clip-path: polygon(0 0, calc(100% - 0.75rem) 0, 100% 50%, calc(100% - 0.75rem) 100%, 0 100%);
  font-size: tokens.$text-size-sm;
}

.rating__label {
  font-weight: tokens.$text-weight-bold;
}

.rating__range {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
}

// White on Green Dark: 6.2:1.
.rating__band--here .rating__bar {
  min-height: tokens.$size-control-sm;
  background: tokens.$color-primary-strong;
  color: tokens.$color-text-on-primary;
  font-size: tokens.$text-size-heading-md;

  .rating__range {
    color: tokens.$color-text-on-primary;
  }
}

// The project's tag points back at its band.
.rating__marker {
  flex: none;
  padding: tokens.$spacing-xs tokens.$spacing-md tokens.$spacing-xs tokens.$spacing-xl;
  background: tokens.$color-text;
  color: tokens.$color-text-on-primary;
  clip-path: polygon(0.75rem 0, 100% 0, 100% 100%, 0.75rem 100%, 0 50%);
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}
</style>

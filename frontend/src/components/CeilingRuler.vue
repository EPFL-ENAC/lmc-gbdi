<template>
  <!-- A scale rule in kg CO₂e per m²: each ceiling hangs from above, the project stands
       below. Further left is lower carbon. -->
  <figure class="ruler" :aria-label="`${benchmark.name}: ${benchmark.band ?? 'not placed'}`">
    <div class="ruler__scale" :class="{ 'ruler__scale--pair': marks }">
      <div class="ruler__axis" />
      <!-- Each mark is a zero-width anchor at its value; line and text hang from it. -->
      <span v-for="t in ticks" :key="`t${t}`" class="ruler__mark" :style="{ left: `${position(t)}%` }">
        <span class="ruler__line ruler__line--tick" />
        <span class="ruler__text ruler__text--tick">{{ kg.format(t) }}</span>
      </span>
      <span
        v-for="ceiling in ceilings"
        :key="ceiling.label"
        class="ruler__mark"
        :style="{ left: `${position(ceiling.upper)}%` }"
      >
        <span class="ruler__line ruler__line--ceiling" />
        <span class="ruler__text ruler__text--ceiling">
          <strong>{{ ceiling.year }}</strong><br />{{ kg.format(ceiling.upper) }}
        </span>
      </span>
      <template v-for="p in points" :key="p.key">
        <span v-if="p.value !== null" class="ruler__mark" :style="{ left: `${position(p.value)}%` }">
          <span class="ruler__line ruler__line--project" :class="`ruler__line--${p.key}`" />
          <span class="ruler__text ruler__text--project" :class="`ruler__text--${p.key}`">
            <span class="ruler__value">{{ one.format(p.value) }}</span>
            <template v-if="!marks"><br />this project</template>
          </span>
        </span>
      </template>
    </div>
    <figcaption class="ruler__caption">kg CO₂e per m². Each mark above is the ceiling for permits filed from that year.</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Benchmark, BenchmarkMark } from '@/api/overview';
import { kg, one } from '@/format';

// `marks`: two buildings standing below the rule instead of the one project.
const props = defineProps<{ benchmark: Benchmark; marks?: BenchmarkMark[] }>();

const points = computed(() => props.marks ?? [{ key: 'project', value: props.benchmark.value }]);

// The band labels name their year ("Within the 2031 ceiling"); the ruler shows the year.
const ceilings = computed(() =>
  props.benchmark.bands
    .filter((band): band is { label: string; upper: number } => band.upper !== null)
    .map((band) => ({ label: band.label, upper: band.upper, year: band.label.match(/\d{4}/)?.[0] ?? band.label })),
);

// Ruler geometry only: from zero to a round hundred past the largest mark.
const max = computed(() => {
  const marks = [...ceilings.value.map((c) => c.upper), ...points.value.map((p) => p.value ?? 0)];
  return Math.ceil((Math.max(...marks) * 1.1) / 100) * 100;
});
const ticks = computed(() => Array.from({ length: max.value / 100 + 1 }, (_, i) => i * 100));
const position = (value: number) => (value / max.value) * 100;
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

$axis-top: 4rem;

.ruler {
  margin: 0;
}

.ruler__scale {
  position: relative;
  height: 10rem;
  margin: 0 tokens.$spacing-xl;
}

.ruler__scale--pair {
  height: 11.5rem;
}

.ruler__axis {
  position: absolute;
  top: $axis-top;
  left: 0;
  right: 0;
  border-top: tokens.$border-width solid tokens.$illustration-stroke;
}

.ruler__mark {
  position: absolute;
  top: 0;
  width: 0;
}

.ruler__line {
  position: absolute;
  left: 0;
}

.ruler__text {
  position: absolute;
  transform: translateX(-50%);
  white-space: nowrap;
  text-align: center;
  font-size: tokens.$text-size-xs;
  font-variant-numeric: tabular-nums;
}

.ruler__line--tick {
  top: $axis-top;
  height: tokens.$spacing-sm;
  border-left: tokens.$border-width solid tokens.$illustration-stroke;
}

.ruler__text--tick {
  top: calc(#{$axis-top} + #{tokens.$spacing-md});
  color: tokens.$color-text-muted;
}

.ruler__line--ceiling {
  top: 2.25rem;
  height: calc(#{$axis-top} - 2.25rem);
  border-left: tokens.$border-width dashed tokens.$color-status-warning;
}

.ruler__text--ceiling {
  top: 0;
}

.ruler__line--project {
  top: $axis-top;
  height: 3rem;
  border-left: 0.125rem solid tokens.$color-primary-strong;
}

.ruler__text--project {
  top: calc(#{$axis-top} + 3.25rem);
  color: tokens.$color-text-muted;
}

.ruler__value {
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-heading-lg;
  color: tokens.$color-primary-strong;
}

.ruler__line--a {
  border-left-color: var(--gbdi-dataviz-green-1);
}

.ruler__line--a + .ruler__text .ruler__value {
  color: var(--gbdi-dataviz-green-1);
}

// B drops one line, so two close values do not overlap.
.ruler__line--b {
  height: 4.75rem;
  border-left-color: var(--gbdi-dataviz-blue-2);
}

.ruler__text--b {
  top: calc(#{$axis-top} + 5rem);
}

.ruler__line--b + .ruler__text .ruler__value {
  color: var(--gbdi-dataviz-blue-2);
}

.ruler__caption {
  margin-top: tokens.$spacing-lg;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

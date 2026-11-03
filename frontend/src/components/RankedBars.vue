<template>
  <figure class="gbdi-card bars-chart" :aria-label="caption">
    <p v-if="bars.length === 0" class="u-text-muted">{{ emptyLabel }}</p>
    <div v-for="bar in drawn" :key="bar.key" class="bars-chart__row">
      <span class="bars-chart__label"><Term :name="bar.label" /></span>
      <div class="bars-chart__track">
        <span
          aria-hidden="true"
          class="bars-chart__bar"
          :class="{ 'bars-chart__bar--missing': bar.missing }"
          :style="{ width: `calc((100% - 5.5rem) * ${bar.fraction})` }"
        />
        <span>{{ bar.display }}</span>
      </div>
    </div>
    <figcaption class="bars-chart__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Term from '@/components/atoms/Term.vue';

export interface Bar {
  key: string;
  label: string;
  value: number;
  display: string; // formatted by the page, in the reader's locale
  missing?: boolean; // data the workbook lacks (Not classified, Undeclared): grey
}

const props = defineProps<{ bars: Bar[]; caption: string; emptyLabel: string }>();

// Chart geometry only: length relative to the largest magnitude (5.5rem stays for the
// value label). ponytail: negatives are drawn by magnitude; their label keeps the sign.
const drawn = computed(() => {
  const largest = Math.max(...props.bars.map((bar) => Math.abs(bar.value)));
  return props.bars.map((bar) => ({ ...bar, fraction: largest === 0 ? 0 : Math.abs(bar.value) / largest }));
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.bars-chart {
  margin: 0;
  padding: tokens.$spacing-xl;
}

.bars-chart__row {
  display: grid;
  // Proportional columns, so the bars keep their length in a narrow card too.
  grid-template-columns: minmax(0, 2fr) minmax(0, 3fr);
  align-items: center;
  gap: tokens.$spacing-md;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.bars-chart__label {
  text-align: right;
}

.bars-chart__track {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
  font-variant-numeric: tabular-nums;
}

.bars-chart__bar {
  flex: none;
  height: tokens.$size-chip;
  min-width: tokens.$spacing-xxs;
  background: var(--gbdi-dataviz-1);
}

.bars-chart__bar--missing {
  background: tokens.$color-data-missing;
}

.bars-chart__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

<template>
  <!-- What each element bar is made of, by mass: one fold per bar, the first one open.
       The backend gives the five heaviest materials and the rest as one row. -->
  <div class="within">
    <details v-for="(element, i) in elements" :key="element.element" class="within__element" :open="i === 0">
      <summary class="within__summary">
        {{ element.element }}
        <span class="within__mass">{{ num.format(element.mass_kg) }} {{ units.mass }}</span>
      </summary>
      <RankedBars
        :bars="bars(element)"
        :caption="`${units.mass} and share of the element's mass.`"
        empty-label="No mass declared in this element."
      />
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ElementMaterial, ElementMaterials, Units } from '@/api/overview';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import { amount, materialName, percent } from '@/format';
import { materialLabel, pairKey } from '@/materials';

const props = defineProps<{ elements: ElementMaterials[]; units: Units }>();
const num = computed(() => amount(props.units));

const bar = (m: ElementMaterial, key: string, label: string): Bar => ({
  key,
  label,
  value: m.mass_kg,
  display: m.share === null ? num.value.format(m.mass_kg) : `${num.value.format(m.mass_kg)}, ${percent.format(m.share)}`,
});
const bars = (element: ElementMaterials): Bar[] => [
  ...element.materials.map((m) => bar(m, pairKey(m), materialName(materialLabel(m)))),
  ...(element.other ? [bar(element.other, 'other', element.other.material)] : []),
];
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.within {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
}

.within__element {
  border-bottom: tokens.$border-width solid tokens.$color-border;
  padding-bottom: tokens.$spacing-sm;
}

// Quasar sets summary to block, which drops the disclosure triangle.
.within__summary {
  display: list-item;
  padding: tokens.$spacing-xs 0;
  cursor: pointer;
  font-size: tokens.$text-size-sm;
  font-weight: tokens.$text-weight-medium;
}

.within__mass {
  margin-left: tokens.$spacing-sm;
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
</style>

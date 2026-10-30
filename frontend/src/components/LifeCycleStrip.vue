<template>
  <figure class="life-strip" :aria-label="`Whole-life carbon by life-cycle stage, ${kg.format(wholeLife)} kg CO₂e`">
    <!-- The life cycle in order, A to C; module D sits beyond the boundary, on the same scale -->
    <div class="life-strip__track">
      <div
        v-for="(stage, i) in stages"
        :key="stage.key"
        class="life-strip__stage"
        :style="{ flexGrow: Math.max(stage.gwp, 0), background: STAGE_COLORS[i] }"
      />
      <div class="life-strip__boundary" aria-hidden="true" />
      <div class="life-strip__beyond" :style="{ flexGrow: Math.abs(moduleD) }" />
    </div>
    <ol class="life-strip__legend">
      <li v-for="(stage, i) in stages" :key="stage.key">
        <span class="life-strip__swatch" :style="{ background: STAGE_COLORS[i] }" />
        <span class="life-strip__name">{{ stage.label }}</span>
        <span class="life-strip__value">{{ kg.format(stage.gwp) }} kg, {{ percent.format(stage.share) }}</span>
      </li>
      <li class="life-strip__outside">
        <span class="life-strip__swatch life-strip__swatch--beyond" />
        <span class="life-strip__name">D1, outside the total</span>
        <span class="life-strip__value">{{ kg.format(moduleD) }} kg</span>
      </li>
    </ol>
    <p v-if="negative.length > 0" class="life-strip__note">
      {{ negative.join(', ') }} below zero, so without length on this strip: read the figure in the legend.
    </p>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { STAGE_COLORS } from '@/dataviz';
import type { StageTotal } from '@/api/overview';
import { kg, percent } from '@/format';

const props = defineProps<{ stages: StageTotal[]; wholeLife: number; moduleD: number }>();

// Shares of a whole only draw positive parts; a negative stage (biogenic carbon
// stored at A1–A3) is named instead of silently missing.
const negative = computed(() => props.stages.filter((s) => s.gwp < 0).map((s) => s.label));

</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.life-strip__note {
  margin: 0;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.life-strip {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}

.life-strip__track {
  display: flex;
  align-items: stretch;
  height: tokens.$size-control-md;
}

.life-strip__stage {
  flex-basis: 0;
  min-width: tokens.$spacing-xxs;
}

.life-strip__boundary {
  flex: none;
  width: tokens.$spacing-lg;
  margin: 0 tokens.$spacing-sm;
  border-left: tokens.$border-width dashed tokens.$color-text-muted;
}

.life-strip__beyond {
  flex-basis: 0;
  border: tokens.$border-width dashed tokens.$color-text-muted;
}

.life-strip__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-sm tokens.$spacing-xl;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-sm;
}

.life-strip__legend li {
  display: grid;
  grid-template-columns: auto auto;
  column-gap: tokens.$spacing-sm;
  align-items: center;
}

.life-strip__swatch {
  width: tokens.$spacing-md;
  height: tokens.$spacing-md;
  border-radius: tokens.$radius-xs;
}

.life-strip__swatch--beyond {
  border: tokens.$border-width dashed tokens.$color-text-muted;
}

.life-strip__value {
  grid-column: 2;
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
}

.life-strip__outside {
  margin-left: auto;
}
</style>

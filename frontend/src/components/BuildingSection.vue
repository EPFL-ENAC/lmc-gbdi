<template>
  <!-- The building drawn by its carbon: one band per element, stacked from the
       foundations up, each band as tall as its share and split by life-cycle stage. -->
  <figure class="section" aria-label="Whole-life carbon by building element, drawn as a section">
    <ul class="section__legend">
      <li v-for="(stage, i) in stages" :key="stage.key">
        <span class="section__swatch" :style="{ background: STAGE_COLORS[i] }" />{{ stage.label }}
      </li>
    </ul>
    <div class="section__drawing" aria-hidden="true">
      <template v-for="band in bands" :key="band.name">
        <div v-if="band.ground" class="section__ground"><span>Ground</span></div>
        <div class="section__row" :style="{ height: `${band.height}rem` }">
          <span class="section__label">{{ band.name }}</span>
          <div class="section__band" :class="{ 'section__band--open': band.split.length === 0 }">
            <span
              v-for="part in band.split"
              :key="part.key"
              :style="{ flexGrow: part.value, background: part.color }"
              :title="part.title"
            />
          </div>
          <span class="section__value">{{ kg.format(band.gwp) }} kg, {{ percent.format(band.share) }}</span>
        </div>
      </template>
    </div>
    <figcaption class="section__caption">
      Band height: the element's share of the whole-life total, in kg CO₂e. Negative stages appear in the table, not
      the drawing.
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ElementStages, ElementTotal, StageTotal } from '@/api/overview';
import { STAGE_COLORS } from '@/dataviz';
import { kg, percent } from '@/format';

const props = defineProps<{
  stages: StageTotal[];
  elements: ElementTotal[];
  elementStages: ElementStages[];
  notClassified: ElementTotal;
}>();

const HEIGHT_REM = 26; // the whole building
const MIN_BAND_REM = 1.75; // a readable band, however small its share
// OpenBDF groups 0 (facilitating works) and 1 (substructure) sit below the ground.
const belowGround = (name: string) => /^[01]\./.test(name);

// Drawing geometry only: heights from the backend's shares, splits from its stages.
const bands = computed(() => {
  const split = (name: string) => {
    const stages = props.elementStages.find((e) => e.element === name)?.gwp_by_stage ?? {};
    return props.stages
      .map((stage, i) => ({
        key: stage.key,
        value: Math.max(stages[stage.key] ?? 0, 0),
        color: STAGE_COLORS[i],
        title: `${stage.label}: ${kg.format(stages[stage.key] ?? 0)} kg CO₂e`,
      }))
      .filter((part) => part.value > 0);
  };
  const topDown = [...props.elements].reverse();
  const firstBelow = topDown.findIndex((e) => belowGround(e.element));
  const rows = topDown.map((e, i) => ({
    name: e.element,
    gwp: e.gwp,
    share: e.share,
    split: split(e.element),
    ground: i === firstBelow,
  }));
  const unclassified = { ...props.notClassified, name: props.notClassified.element, split: [], ground: false };
  return [...(props.notClassified.gwp !== 0 ? [unclassified] : []), ...rows].map((band) => ({
    ...band,
    height: Math.max(MIN_BAND_REM, HEIGHT_REM * Math.abs(band.share)),
  }));
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.section {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}

.section__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-lg;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.section__legend li {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-xs;
}

.section__swatch {
  width: tokens.$spacing-md;
  height: tokens.$spacing-md;
  border-radius: tokens.$radius-xs;
}

.section__drawing {
  display: flex;
  flex-direction: column;
}

.section__row {
  display: grid;
  grid-template-columns: minmax(0, 15rem) minmax(0, 1fr) minmax(0, 11rem);
  align-items: stretch;
  gap: tokens.$spacing-lg;
  font-size: tokens.$text-size-sm;
}

.section__label,
.section__value {
  align-self: center;
}

.section__label {
  text-align: right;
}

.section__value {
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
}

// Bands share their outlines like a sectional drawing: 1px Grey Dark, no gaps.
.section__band {
  display: flex;
  border: tokens.$illustration-stroke-width solid tokens.$illustration-stroke;
  border-top-width: 0;
}

.section__row:first-child .section__band,
.section__ground + .section__row .section__band {
  border-top-width: tokens.$illustration-stroke-width;
}

.section__band > span {
  flex-basis: 0;
}

.section__band--open {
  border-style: dashed;
  border-top-width: tokens.$illustration-stroke-width;
  background: tokens.$color-surface;
}

.section__ground {
  position: relative;
  height: tokens.$spacing-xl;
  margin: 0 -#{tokens.$spacing-lg};
  border-bottom: tokens.$border-width dashed tokens.$color-text-muted;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.section__ground span {
  position: absolute;
  right: 0;
  bottom: tokens.$spacing-xs;
}

.section__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

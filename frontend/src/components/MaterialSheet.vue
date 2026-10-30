<template>
  <!-- One material as a product data sheet, the way an FDES or EPD presents it:
       identity, the declared figures, then the result module by module. -->
  <article class="sheet-card">
    <header class="sheet-card__head">
      <span class="sheet-card__rank">{{ rank }}</span>
      <div>
        <h3 class="sheet-card__name">{{ hotspot.material || 'No material name' }}</h3>
        <p class="sheet-card__product">{{ hotspot.epd_product }}</p>
      </div>
    </header>
    <dl class="sheet-card__figures">
      <div>
        <dt>kg CO₂e, whole life</dt>
        <dd>{{ kg.format(hotspot.gwp) }}</dd>
      </div>
      <div>
        <dt>Share of the building</dt>
        <dd>{{ percent.format(hotspot.share) }}</dd>
      </div>
      <div>
        <dt>Mass, kg</dt>
        <dd>{{ kg.format(hotspot.mass_kg) }}</dd>
      </div>
      <div>
        <dt>kg CO₂e per kg</dt>
        <dd>{{ figure(hotspot.gwp_per_kg, three) }}</dd>
      </div>
    </dl>
    <table class="sheet-card__modules">
      <caption>kg CO₂e by life-cycle stage</caption>
      <tbody>
        <tr v-for="(stage, i) in stages" :key="stage.key">
          <th scope="row">{{ stage.label }}</th>
          <td class="sheet-card__bar-cell">
            <span
              class="sheet-card__bar"
              :style="{ width: `${barWidth(hotspot.gwp_by_stage[stage.key])}%`, background: STAGE_COLORS[i] }"
            />
          </td>
          <td class="num">{{ kg.format(hotspot.gwp_by_stage[stage.key]) }}</td>
        </tr>
      </tbody>
    </table>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { MaterialHotspot, StageTotal } from '@/api/overview';
import { STAGE_COLORS } from '@/dataviz';
import { figure, kg, percent, three } from '@/format';

const props = defineProps<{ hotspot: MaterialHotspot; stages: StageTotal[]; rank: number }>();

// Bar geometry only: against the largest positive stage of this material; a
// negative stage keeps its signed figure and draws no bar.
const largest = computed(() => Math.max(...Object.values(props.hotspot.gwp_by_stage), 0));
const barWidth = (value: number) => (value > 0 && largest.value > 0 ? (value / largest.value) * 100 : 0);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.sheet-card {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
  padding: tokens.$spacing-xl;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-card;
  background: tokens.$color-surface;
}

.sheet-card__head {
  display: flex;
  gap: tokens.$spacing-md;
  align-items: baseline;
}

.sheet-card__rank {
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-md;
  line-height: 1;
  color: tokens.$color-text-lead;
  font-variant-numeric: tabular-nums;
}

.sheet-card__name {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-md;
  font-weight: tokens.$text-weight-bold;
}

.sheet-card__product {
  margin: 0;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.sheet-card__figures {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0;
  border-top: tokens.$border-width solid tokens.$color-border;
  border-bottom: tokens.$border-width solid tokens.$color-border;
}

.sheet-card__figures > div {
  padding: tokens.$spacing-sm 0;
}

.sheet-card__figures dt {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.sheet-card__figures dd {
  margin: 0;
  font-size: tokens.$text-size-lg;
  font-variant-numeric: tabular-nums;
}

.sheet-card__modules {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}

.sheet-card__modules caption {
  text-align: left;
  padding-bottom: tokens.$spacing-xs;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.sheet-card__modules th {
  width: 4rem;
  text-align: left;
  font-weight: tokens.$text-weight-regular;
}

.sheet-card__modules td,
.sheet-card__modules th {
  padding: tokens.$spacing-xxs 0;
}

.sheet-card__bar-cell {
  padding-right: tokens.$spacing-md;
}

.sheet-card__bar {
  display: block;
  height: tokens.$spacing-md;
}

.sheet-card__modules .num {
  width: 6rem;
  text-align: right;
}
</style>

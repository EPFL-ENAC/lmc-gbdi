<template>
  <!-- One list, two measures: ranked by carbon or by mass, each row shows both, so a
       material heavy in one and light in the other reads on one line (review #81). -->
  <figure class="gbdi-card ranking" :aria-label="caption">
    <div class="ranking__head">
      <q-btn-toggle
        v-model="rankBy"
        :options="RANKINGS"
        no-caps
        unelevated
        dense
        toggle-color="primary"
        color="white"
        text-color="dark"
        class="ranking__switch"
      />
    </div>
    <p v-if="materials.length === 0" class="u-text-muted">No materials.</p>
    <table v-else class="ranking__table">
      <thead>
        <tr>
          <th scope="col" class="ranking__label">Material</th>
          <th scope="col" :class="{ 'ranking__by': rankBy === 'carbon' }">Whole-life carbon, kg CO₂e</th>
          <th scope="col" :class="{ 'ranking__by': rankBy === 'mass' }">Mass, kg</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.key">
          <th scope="row" class="ranking__label"><Term :name="row.label" /></th>
          <td v-for="measure in row.measures" :key="measure.key">
            <span class="ranking__track">
              <span
                aria-hidden="true"
                class="ranking__bar"
                :class="{ 'ranking__bar--other': measure.key !== rankBy }"
                :style="{ width: `calc((100% - 5.5rem) * ${measure.fraction})` }"
              />
              <span>{{ kg.format(measure.value) }}</span>
            </span>
          </td>
        </tr>
      </tbody>
    </table>
    <ShowMore v-model="open" :count="Math.max(sorted.length - TOP_MATERIALS, 0)" />
    <figcaption class="ranking__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { MaterialHotspot } from '@/api/overview';
import ShowMore from '@/components/atoms/ShowMore.vue';
import Term from '@/components/atoms/Term.vue';
import { kg } from '@/format';
import { materialLabel, pairKey, RANKINGS, ranked, TOP_MATERIALS, type RankBy } from '@/materials';

const props = defineProps<{ materials: MaterialHotspot[]; caption: string }>();

const rankBy = ref<RankBy>('carbon');
const open = ref(false);
const sorted = computed(() => ranked(props.materials, rankBy.value));

// Each measure on its own scale, over every material, so the bars keep their length
// when the list opens. ponytail: negatives are drawn by magnitude; the label keeps the sign.
const largest = computed(() => ({
  carbon: Math.max(0, ...props.materials.map((m) => Math.abs(m.gwp))),
  mass: Math.max(0, ...props.materials.map((m) => m.mass_kg)),
}));
const fraction = (value: number, by: RankBy) => (largest.value[by] ? Math.abs(value) / largest.value[by] : 0);

const rows = computed(() =>
  (open.value ? sorted.value : sorted.value.slice(0, TOP_MATERIALS)).map((m) => ({
    key: pairKey(m),
    label: materialLabel(m),
    measures: [
      { key: 'carbon' as const, value: m.gwp, fraction: fraction(m.gwp, 'carbon') },
      { key: 'mass' as const, value: m.mass_kg, fraction: fraction(m.mass_kg, 'mass') },
    ],
  })),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.ranking {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
  margin: 0;
  padding: tokens.$spacing-xl;
}

.ranking__switch {
  border: tokens.$border-width solid tokens.$color-border;
}

.ranking__table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
}

.ranking__table th,
.ranking__table td {
  padding: tokens.$spacing-xxs tokens.$spacing-sm;
  font-weight: tokens.$text-weight-regular;
  text-align: left;
}

.ranking__table thead th {
  padding-bottom: tokens.$spacing-sm;
}

// The column that sets the order reads as the heading that matters.
.ranking__by {
  color: tokens.$color-text;
  font-weight: tokens.$text-weight-medium !important;
}

.ranking__label {
  width: 30%;
  text-align: right !important;
}

.ranking__track {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
}

.ranking__bar {
  flex: none;
  height: tokens.$size-chip;
  min-width: tokens.$spacing-xxs;
  background: var(--gbdi-dataviz-1);
}

// The measure that does not set the order: same material, quieter.
.ranking__bar--other {
  background: var(--gbdi-dataviz-green-3);
}

.ranking__caption {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>

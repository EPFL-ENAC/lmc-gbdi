<template>
  <!-- Variant 6, "Passport": the building as the materials it is made of. A material
       passport's mass composition (as in Madaster), then one data sheet per material,
       laid out the way an FDES or EPD presents a product (as in INIES). -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <template v-else>
      <header>
        <h1>
          {{ overview.project.project_name ?? 'Unnamed project' }}<br />
          <span class="text-display-lead">Material passport</span>
        </h1>
        <p class="text-lead">
          {{ kg.format(overview.total_mass_kg) }} kg of materials, from {{ kg.format(overview.rows_read) }} bill of
          materials rows, data from {{ overview.project.lca_database ?? 'an undeclared database' }}.
        </p>
      </header>

      <!-- The same ten materials in two walls, by mass and by carbon, one colour each:
           heavy is not the same as intense. The switch picks which ranking sets the ten. -->
      <section class="passport__section">
        <div class="passport__head">
          <h2 class="passport__title">What it weighs, what it emits</h2>
          <q-btn-toggle
            v-model="rankBy"
            :options="RANKINGS"
            no-caps
            unelevated
            toggle-color="primary"
            color="white"
            text-color="dark"
            class="passport__switch"
          />
        </div>
        <p class="u-text-muted">
          {{ rankBy === 'mass' ? 'The ten heaviest materials, and the carbon each carries.' : 'The ten materials with the most whole-life carbon, and what each weighs.' }}
          One colour per material in both walls; one brick is one per cent.
        </p>
        <div class="grid-2-col passport__walls">
          <figure class="passport__wall">
            <figcaption>Mass, {{ kg.format(overview.total_mass_kg) }} kg</figcaption>
            <BrickWall :parts="ranked.map((r) => ({ color: r.color, share: r.share_of_mass ?? 0 }))" label="Mass by material" />
          </figure>
          <figure class="passport__wall">
            <figcaption>Whole-life carbon, modules A to C, {{ kg.format(overview.headline.whole_life) }} kg CO₂e</figcaption>
            <BrickWall :parts="ranked.map((r) => ({ color: r.color, share: r.share }))" label="Whole-life carbon by material" />
          </figure>
        </div>
        <table class="passport__legend">
          <thead>
            <tr>
              <th scope="col">Material</th>
              <th scope="col" class="num">kg</th>
              <th scope="col" class="num">Share of the mass</th>
              <th scope="col" class="num">kg CO₂e</th>
              <th scope="col" class="num">Share of the carbon</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in ranked" :key="row.key">
              <th scope="row">
                <span class="passport__swatch" :style="{ background: row.color }" />{{ row.label }}
                <span class="passport__product">{{ row.epd_product }}</span>
              </th>
              <td class="num">{{ kg.format(row.mass_kg) }}</td>
              <td class="num">{{ row.share_of_mass === null ? 'no mass declared' : percent.format(row.share_of_mass) }}</td>
              <td class="num">{{ kg.format(row.gwp) }}</td>
              <td class="num">{{ percent.format(row.share) }}</td>
            </tr>
            <tr>
              <th scope="row"><span class="passport__swatch" :style="{ background: OTHER_COLOR }" />Every other material</th>
              <td colspan="4" />
            </tr>
          </tbody>
        </table>
      </section>

      <section class="passport__section">
        <h2 class="passport__title">Material by material</h2>
        <p class="u-text-muted">
          The ten materials with the most whole-life carbon. Heavy is not the same as intense: compare the mass with
          the carbon per kg.
        </p>
        <div class="grid-2-col">
          <MaterialSheet
            v-for="(hotspot, i) in overview.material_hotspots"
            :key="`${hotspot.material}|${hotspot.epd_product}`"
            :hotspot="hotspot"
            :stages="overview.stages"
            :rank="i + 1"
          />
        </div>
      </section>

      <section class="passport__section">
        <h2 class="passport__title">How the data was declared</h2>
        <p>{{ dataTypeSentence }}</p>
        <ProjectFieldsTable :fields="overview.project_fields" />
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import BrickWall from '@/components/BrickWall.vue';
import MaterialSheet from '@/components/MaterialSheet.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import { useOverview } from '@/composables/useOverview';
import { MATERIAL_COLORS, OTHER_COLOR } from '@/dataviz';
import { kg, percent, WEIGHTING } from '@/format';

const { overview, error } = useOverview();

const RANKINGS = [
  { label: 'Top 10 by mass', value: 'mass' },
  { label: 'Top 10 by carbon', value: 'carbon' },
];
const rankBy = ref<'mass' | 'carbon'>('mass');

// One row per material of the chosen ranking, both measures from the backend; the
// colour follows the rank, so a material has the same one in both walls.
const ranked = computed(() => {
  const o = overview.value;
  if (o === null) return [];
  const rows = rankBy.value === 'mass' ? o.mass_hotspots : o.material_hotspots;
  return rows.map((h, i) => ({
    key: `${h.material}|${h.epd_product}`,
    label: h.material || h.epd_product,
    epd_product: h.material ? h.epd_product : '',
    mass_kg: h.mass_kg,
    share_of_mass: h.share_of_mass,
    gwp: h.gwp,
    share: h.share,
    color: MATERIAL_COLORS[i],
  }));
});

const dataTypeSentence = computed(() => {
  const o = overview.value;
  if (o === null) return '';
  if (o.data_types.length === 0) return WEIGHTING[o.data_type_weighting];
  const undeclared = o.data_types.find((d) => d.key === 'undeclared')?.share ?? 0;
  return `Data type undeclared: ${percent.format(undeclared)}. ${WEIGHTING[o.data_type_weighting]}`;
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.passport__section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.passport__section p {
  margin: 0;
}

.passport__head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: tokens.$spacing-md;
}

.passport__switch {
  border: tokens.$border-width solid tokens.$color-border;
}

.passport__walls {
  column-gap: tokens.$spacing-page;
}

.passport__wall {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
  margin: 0;
  font-size: tokens.$text-size-sm;
}

.passport__legend {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}

.passport__legend th,
.passport__legend td {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
  font-weight: tokens.$text-weight-regular;
}

.passport__legend thead th {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.passport__legend .num {
  text-align: right;
  white-space: nowrap;
}

.passport__swatch {
  display: inline-block;
  width: tokens.$spacing-lg;
  height: tokens.$spacing-sm;
  margin-right: tokens.$spacing-sm;
  border-radius: tokens.$radius-xs;
}

.passport__product {
  display: block;
  padding-left: calc(#{tokens.$spacing-lg} + #{tokens.$spacing-sm});
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.passport__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}
</style>

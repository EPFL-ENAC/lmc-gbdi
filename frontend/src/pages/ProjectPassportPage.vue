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

      <!-- The same wall twice: by mass, then by carbon. Heavy is not the same as intense. -->
      <section class="passport__section grid-2-col">
        <div class="passport__column">
          <h2 class="passport__title">What it weighs</h2>
          <MaterialBricks :items="massBricks" :total="overview.total_mass_kg" unit="kg" caption="Mass by material" />
        </div>
        <div class="passport__column">
          <h2 class="passport__title">What it emits</h2>
          <MaterialBricks
            :items="carbonBricks"
            :total="overview.headline.whole_life"
            unit="kg CO₂e"
            caption="Whole-life carbon by material, modules A to C"
          />
        </div>
      </section>

      <section class="passport__section">
        <h2 class="passport__title">What it emits, material by material</h2>
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
import { computed } from 'vue';
import MaterialBricks, { type Brick } from '@/components/MaterialBricks.vue';
import MaterialSheet from '@/components/MaterialSheet.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import { useOverview } from '@/composables/useOverview';
import { kg, percent, WEIGHTING } from '@/format';

const { overview, error } = useOverview();

const label = (h: { material: string; epd_product: string }) => h.material || h.epd_product;
const massBricks = computed<Brick[]>(() =>
  (overview.value?.mass_hotspots ?? []).map((h) => ({
    key: `${h.material}|${h.epd_product}`,
    label: label(h),
    value: h.mass_kg,
    share: h.share_of_mass,
  })),
);
const carbonBricks = computed<Brick[]>(() =>
  (overview.value?.material_hotspots ?? []).map((h) => ({
    key: `${h.material}|${h.epd_product}`,
    label: label(h),
    value: h.gwp,
    share: h.share,
  })),
);

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

.passport__section.grid-2-col {
  display: grid;
  align-items: start;
  column-gap: tokens.$spacing-page;
}

.passport__column {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}

.passport__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}
</style>

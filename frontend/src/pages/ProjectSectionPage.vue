<template>
  <!-- Variant 2, "Section": the building is the chart. One statement in display type,
       then the elements stacked from the foundations up, then the life cycle in order. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <template v-else>
      <header class="section-page__head">
        <p class="section-page__name">{{ overview.project.project_name ?? 'Unnamed project' }}</p>
        <h1 class="section-page__statement">
          {{ kg.format(overview.headline.whole_life) }} kg CO₂e over
          {{ figure(overview.project.reference_study_period_years, kg) }} years
          <span class="text-display-lead">
            {{ figure(overview.headline.per_m2_useful, one) }} kg per m<sup>2</sup> of useful floor area
          </span>
        </h1>
      </header>

      <section class="section-page__block">
        <h2 class="section-page__title">Where it sits in the building</h2>
        <BuildingSection
          :stages="overview.stages"
          :elements="overview.elements"
          :element-stages="overview.element_stages"
          :not-classified="overview.not_classified"
        />
        <details>
          <summary class="section-page__more">Show the figures by element and stage</summary>
          <StageByElement :stages="overview.stages" :rows="overview.element_stages" />
        </details>
      </section>

      <section class="section-page__block">
        <h2 class="section-page__title">When it is emitted</h2>
        <LifeCycleStrip
          :stages="overview.stages"
          :whole-life="overview.headline.whole_life"
          :module-d="overview.headline.module_d1"
        />
      </section>

      <section class="section-page__block">
        <h2 class="section-page__title">What it is made of</h2>
        <div class="grid-2-col">
          <RankedBars :bars="carbonBars" caption="Heaviest in carbon, kg CO₂e over the whole life." empty-label="No materials." />
          <RankedBars :bars="massBars" caption="Heaviest in mass, kg." empty-label="No materials." />
        </div>
      </section>

      <section class="section-page__block">
        <h2 class="section-page__title">How the data was declared</h2>
        <p class="section-page__note">{{ dataTypeSentence }}</p>
        <ModuleChecks
          :checks="overview.module_checks"
          :rows-read="overview.rows_read"
          :declared-without-result="overview.modules_declared_without_result"
          :result-without-declaration="overview.modules_with_undeclared_result"
        />
      </section>

      <section class="section-page__block">
        <h2 class="section-page__title">Project details</h2>
        <ProjectFieldsTable :fields="overview.project_fields" />
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import BuildingSection from '@/components/BuildingSection.vue';
import LifeCycleStrip from '@/components/LifeCycleStrip.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import StageByElement from '@/components/StageByElement.vue';
import { useOverview } from '@/composables/useOverview';
import { figure, kg, one, percent, WEIGHTING } from '@/format';

const { overview, error } = useOverview();

const materialBars = <T extends { material: string; epd_product: string }>(rows: T[], value: (row: T) => number) =>
  rows.map((m) => ({
    key: `${m.material}|${m.epd_product}`,
    label: m.material || m.epd_product,
    value: value(m),
    display: kg.format(value(m)),
  }));
const carbonBars = computed<Bar[]>(() => materialBars(overview.value?.material_hotspots ?? [], (m) => m.gwp));
const massBars = computed<Bar[]>(() => materialBars(overview.value?.mass_hotspots ?? [], (m) => m.mass_kg));

// One sentence instead of a chart when every material says the same thing.
const dataTypeSentence = computed(() => {
  const o = overview.value;
  if (o === null) return '';
  if (o.data_types.length === 0) return WEIGHTING[o.data_type_weighting];
  const declared = o.data_types.filter((d) => d.key !== 'undeclared' && d.share > 0);
  const undeclared = o.data_types.find((d) => d.key === 'undeclared')?.share ?? 0;
  const parts = declared.map((d) => `${d.label.toLowerCase()} ${percent.format(d.share)}`);
  const lead = declared.length === 0 ? 'No material declares its data type yet.' : `Data types: ${parts.join(', ')}.`;
  return `${lead} Undeclared: ${percent.format(undeclared)}. ${WEIGHTING[o.data_type_weighting]}`;
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;


.section-page__name {
  margin: 0 0 tokens.$spacing-sm;
  font-size: tokens.$text-size-heading-lg;
}

// The statement is the page's display line: SK Modernist, the second half faded.
.section-page__statement {
  margin: 0;
  font-size: tokens.$text-size-display-lg;
}

.section-page__statement .text-display-lead {
  display: block;
}

.section-page__statement sup {
  font-size: 0.45em;
  line-height: 0;
}

.section-page__block {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.section-page__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.section-page__note {
  margin: 0;
  max-width: 42rem;
}

.section-page__more {
  cursor: pointer;
  margin-bottom: tokens.$spacing-lg;
  color: tokens.$color-text-link;
  text-decoration: underline;
  text-underline-offset: 0.125rem;
}
</style>

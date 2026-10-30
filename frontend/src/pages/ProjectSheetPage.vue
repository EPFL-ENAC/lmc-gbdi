<template>
  <!-- Variant 3, "Sheet": a construction drawing sheet for the analyst. A title block,
       the figures in one row, then panels on a shared hairline grid; everything at once. -->
  <q-page class="sheet-page">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <article v-else class="sheet">
      <header class="sheet__title">
        <div>
          <h1 class="sheet__name">{{ overview.project.project_name ?? 'Unnamed project' }}</h1>
          <p class="sheet__subtitle">Building carbon overview</p>
        </div>
        <dl class="sheet__block">
          <div v-for="item in titleBlock" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
      </header>

      <dl class="sheet__figures">
        <div v-for="item in figures" :key="item.label" class="sheet__figure">
          <dt>{{ item.label }}</dt>
          <dd>{{ item.value }}</dd>
        </div>
      </dl>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Life-cycle stages</h2>
        <LifeCycleStrip
          :stages="overview.stages"
          :whole-life="overview.headline.whole_life"
          :module-d="overview.headline.module_d1"
        />
      </section>

      <div class="sheet__pair">
        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Element by stage</h2>
          <StageMatrix :stages="overview.stages" :rows="overview.element_stages" />
          <p class="sheet__note">
            Not classified: {{ kg.format(overview.not_classified.gwp) }} kg CO₂e,
            {{ percent.format(overview.not_classified.share) }} of the total.
          </p>
        </section>
        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Materials, mass against carbon</h2>
          <IntensityPlot :hotspots="overview.material_hotspots" />
        </section>
      </div>

      <div class="sheet__pair">
        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Material hotspots</h2>
          <q-table
            flat
            dense
            hide-bottom
            :rows="overview.material_hotspots"
            :columns="hotspotColumns"
            :row-key="(m: MaterialHotspot) => `${m.material}|${m.epd_product}`"
            :pagination="{ rowsPerPage: 0 }"
            no-data-label="No materials in this project."
          />
        </section>
        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Data</h2>
          <RankedBars :bars="dataTypeBars" :caption="WEIGHTING[overview.data_type_weighting]" empty-label="Not computed." />
          <ModuleChecks
            :checks="overview.module_checks"
            :rows-read="overview.rows_read"
            :declared-without-result="overview.modules_declared_without_result"
            :result-without-declaration="overview.modules_with_undeclared_result"
          />
        </section>
      </div>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Project details</h2>
        <ProjectFieldsTable :fields="overview.project_fields" />
      </section>
    </article>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTableColumn } from 'quasar';
import type { MaterialHotspot } from '@/api/overview';
import IntensityPlot from '@/components/IntensityPlot.vue';
import LifeCycleStrip from '@/components/LifeCycleStrip.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import StageMatrix from '@/components/StageMatrix.vue';
import { useOverview } from '@/composables/useOverview';
import { figure, kg, one, percent, three, two, WEIGHTING } from '@/format';

const { overview, error } = useOverview();

const titleBlock = computed(() => {
  const p = overview.value?.project;
  return [
    { label: 'Project', value: p?.project_id ?? 'not declared' },
    { label: 'Country', value: p?.country ?? 'not declared' },
    { label: 'Gross floor area', value: `${figure(p?.gross_floor_area_m2 ?? null, kg)} m²` },
    { label: 'Study period', value: `${figure(p?.reference_study_period_years ?? null, kg)} years` },
    { label: 'Method', value: p?.lcia_methodology ?? 'not declared' },
  ];
});

const figures = computed(() => {
  const h = overview.value?.headline;
  if (h === undefined) return [];
  return [
    { label: 'kg CO₂e, whole life (A–C)', value: kg.format(h.whole_life) },
    { label: 'kg CO₂e, upfront (A1–A5)', value: kg.format(h.upfront) },
    { label: 'kg CO₂e per m² useful floor area', value: figure(h.per_m2_useful, one) },
    { label: 'kg CO₂e per m² and year', value: figure(h.per_m2_useful_per_year, two) },
    { label: 'kg CO₂e, module D1, outside the total', value: kg.format(h.module_d1) },
  ];
});

const hotspotColumns: QTableColumn<MaterialHotspot>[] = [
  // No EPD column here, so an unnamed material shows its EPD product instead.
  {
    name: 'material',
    label: 'Material',
    field: (m) => m.material || m.epd_product,
    align: 'left',
  },
  { name: 'gwp', label: 'kg CO₂e', field: 'gwp', format: (v: number) => kg.format(v), align: 'right' },
  { name: 'share', label: 'Share', field: 'share', format: (v: number) => percent.format(v), align: 'right' },
  { name: 'mass', label: 'Mass (kg)', field: 'mass_kg', format: (v: number) => kg.format(v), align: 'right' },
  {
    name: 'intensity',
    label: 'Per kg',
    field: 'gwp_per_kg',
    format: (v: number | null) => figure(v, three),
    align: 'right',
  },
];

const dataTypeBars = computed<Bar[]>(() =>
  (overview.value?.data_types ?? []).map((d) => ({
    key: d.key,
    label: d.label,
    value: d.share,
    display: percent.format(d.share),
    muted: d.key === 'undeclared',
  })),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

// The sheet lies on a Green-Grey Card desk; its panels share one hairline grid.
.sheet-page {
  padding: tokens.$spacing-xl tokens.$spacing-lg;
  background: tokens.$color-surface-muted;
}

.sheet {
  max-width: tokens.$layout-page-width;
  margin: 0 auto;
  background: tokens.$color-surface;
  border: tokens.$border-width solid tokens.$color-border-control;
  border-radius: tokens.$radius-panel;
  overflow: hidden;
}

.sheet > * + * {
  border-top: tokens.$border-width solid tokens.$color-border-control;
}

.sheet__title {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: tokens.$spacing-xl;
  padding: tokens.$spacing-xl;
}

.sheet__name {
  margin: 0;
  font-size: tokens.$text-size-display-md;
}

.sheet__subtitle {
  margin: 0;
  color: tokens.$color-text-lead;
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-md;
}

// The title block of a drawing: small labels over values, ruled apart.
.sheet__block {
  display: flex;
  flex-wrap: wrap;
  margin: 0;
  align-self: flex-end;
}

.sheet__block > div {
  padding: 0 tokens.$spacing-lg;
  border-left: tokens.$border-width solid tokens.$color-border-control;
}

.sheet__block dt {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.sheet__block dd {
  margin: 0;
  font-size: tokens.$text-size-sm;
}

.sheet__figures {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  margin: 0;
}

.sheet__figure {
  display: flex;
  flex-direction: column-reverse;
  justify-content: flex-end;
  gap: tokens.$spacing-xs;
  padding: tokens.$spacing-lg tokens.$spacing-xl;
  border-left: tokens.$border-width solid tokens.$color-border-control;
}

.sheet__figure:first-child {
  border-left: 0;
}

.sheet__figure dd {
  margin: 0;
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-md;
  line-height: tokens.$text-line-height-tight;
}

.sheet__figure dt {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.sheet__pair {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.sheet__pair > .sheet__panel + .sheet__panel {
  border-left: tokens.$border-width solid tokens.$color-border-control;
}

.sheet__panel {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
  padding: tokens.$spacing-xl;
}

.sheet__panel-title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-base;
  font-weight: tokens.$text-weight-medium;
}

.sheet__note {
  margin: 0;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

@media (max-width: 1199px) {
  .sheet__pair {
    grid-template-columns: minmax(0, 1fr);
  }

  .sheet__pair > .sheet__panel + .sheet__panel {
    border-left: 0;
    border-top: tokens.$border-width solid tokens.$color-border-control;
  }
}
</style>

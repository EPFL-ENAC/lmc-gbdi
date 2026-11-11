<template>
  <!-- The one view of a building (globalbuildingdatainitiative/org#97), a drawing sheet
       read top to bottom: what the project is, then its mass, its emissions, its
       materials, and how far its data can be trusted. -->
  <q-page class="sheet-page">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <article v-else class="sheet">
      <!-- Project info -->
      <header class="sheet__title">
        <div>
          <h1 class="sheet__name">{{ overview.project.project_name ?? 'Unnamed project' }}</h1>
          <p class="sheet__subtitle">Building carbon overview</p>
        </div>
        <dl class="sheet__block">
          <div v-for="field in titleBlock" :key="field.code">
            <dt>{{ field.label }}</dt>
            <dd>{{ fieldText(field.value) }}</dd>
          </div>
        </dl>
      </header>

      <section class="sheet__panel" aria-label="Headline results">
        <div class="grid-3-col">
          <BigNumber :value="kg.format(overview.headline.whole_life)" tone="green">
            kg CO₂e over the whole life cycle, modules A to C.
          </BigNumber>
          <BigNumber :value="figure(overview.headline.per_m2_gross, one)" tone="blue">
            kg CO₂e per m² of gross floor area{{ usefulAside(overview.headline.per_m2_useful) }}.
          </BigNumber>
          <BigNumber :value="figure(overview.headline.per_m2_gross_per_year, two)" tone="purple">
            <template v-if="overview.project.reference_study_period_years !== null">
              kg CO₂e per m² of gross floor area and year, over
              {{ kg.format(overview.project.reference_study_period_years) }} years.
            </template>
            <template v-else>kg CO₂e per m² and year: the workbook declares no study period to divide by.</template>
          </BigNumber>
        </div>
        <p class="sheet__note">
          Computed from the OpenBDF workbook, {{ kg.format(overview.rows_read) }} bill of materials rows, data from
          {{ overview.project.lca_database ?? 'an undeclared database' }}.
        </p>
      </section>

      <!-- Mass -->
      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Building elements</h2>
        <p class="u-text-muted">
          {{ kg.format(overview.total_mass_kg) }} kg of materials. Whole-life carbon by OpenBDF element, Tier 2, in
          classification order.
        </p>
        <BarsWithTable
          :bars="elementRows.map((e) => bar(e.element, e.gwp, e.share, e === overview!.not_classified))"
          :rows="elementRows"
          :columns="elementColumns"
          row-key="element"
          caption="kg CO₂e and share of the whole-life total. Rows without an element code stay visible."
          empty-label="No classified building elements in this project."
        />
      </section>

      <!-- Emissions: the stages as a strip, then the same stages on a timeline. -->
      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Life-cycle stages</h2>
        <LifeCycleStrip
          :stages="overview.stages"
          :whole-life="overview.headline.whole_life"
          :module-d="overview.headline.module_d1"
        />
      </section>

      <section class="sheet__panel">
        <TimeSection :overview="overview" />
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Element by stage</h2>
        <StageMatrix :stages="overview.stages" :rows="overview.element_stages" />
        <p class="sheet__note">
          Not classified: {{ kg.format(overview.not_classified.gwp) }} kg CO₂e,
          {{ percent.format(overview.not_classified.share) }} of the total.
        </p>
      </section>

      <!-- Materials -->
      <MaterialWalls :overview="overview" />

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Materials, mass against carbon</h2>
        <IntensityPlot :hotspots="overview.material_hotspots" />
      </section>

      <!-- Data quality -->
      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Data type profile</h2>
        <RankedBars :bars="dataTypeBars" :caption="WEIGHTING[overview.data_type_weighting]" empty-label="Not computed." />
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Data checks</h2>
        <p class="u-text-muted">Each life-cycle module declared in scope, against the results present.</p>
        <ModuleChecks
          :checks="overview.module_checks"
          :rows-read="overview.rows_read"
          :declared-without-result="overview.modules_declared_without_result"
          :result-without-declaration="overview.modules_with_undeclared_result"
        />
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Project details</h2>
        <p class="u-text-muted">General Information, as declared. Choose the columns to compare.</p>
        <ProjectFieldsTable :fields="overview.project_fields" />
      </section>
    </article>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTableColumn } from 'quasar';
import type { ElementTotal } from '@/api/overview';
import BarsWithTable from '@/components/BarsWithTable.vue';
import IntensityPlot from '@/components/IntensityPlot.vue';
import LifeCycleStrip from '@/components/LifeCycleStrip.vue';
import MaterialWalls from '@/components/MaterialWalls.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import BigNumber from '@/components/molecules/BigNumber.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import StageMatrix from '@/components/StageMatrix.vue';
import TimeSection from '@/components/TimeSection.vue';
import { useOverview } from '@/composables/useOverview';
import { fieldText, figure, kg, one, percent, two, usefulAside, WEIGHTING } from '@/format';

// The title block, in the order of the issue: what the project is, then the five
// attributes that decide whether two results compare (#85).
const TITLE_FIELDS = [
  'project_id',
  'project_country',
  'building_use_type',
  'building_structure_type',
  'building_gross_floor_area',
  'building_gross_floor_area_standard',
  'lca_reference_study_period',
  'project_assessment_type',
  'project_phase_common',
  'lca_cycle_system_boundary',
  'lcia_methodology',
  'lca_biogenic_method',
  'lca_temporal_approach',
  'lca_lci_modeling_approach',
];

const { overview, error } = useOverview();

const titleBlock = computed(() =>
  (overview.value?.project_fields ?? [])
    .filter((f) => TITLE_FIELDS.includes(f.code))
    .sort((a, b) => TITLE_FIELDS.indexOf(a.code) - TITLE_FIELDS.indexOf(b.code)),
);

// Chart and table read the same backend rows, in the backend's order.
const elementRows = computed(() =>
  overview.value === null
    ? []
    : [...overview.value.elements, overview.value.other_classified, overview.value.not_classified],
);
const bar = (label: string, value: number, share: number, missing: boolean): Bar => ({
  key: label,
  label,
  value,
  display: `${kg.format(value)}, ${percent.format(share)}`,
  missing,
});
const elementColumns: QTableColumn<ElementTotal>[] = [
  { name: 'element', label: 'Element', field: 'element', align: 'left' },
  { name: 'gwp', label: 'GWP (kg CO₂e)', field: 'gwp', format: (v: number) => kg.format(v), align: 'right' },
  { name: 'share', label: 'Share', field: 'share', format: (v: number) => percent.format(v), align: 'right' },
];

const dataTypeBars = computed<Bar[]>(() =>
  (overview.value?.data_types ?? []).map((d) => ({
    key: d.key,
    label: d.label,
    value: d.share,
    display: percent.format(d.share),
    missing: d.key === 'undeclared',
  })),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

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
</style>

<template>
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <template v-else>
      <section>
        <h1>
          {{ overview.project.project_name ?? 'Unnamed project' }}<br />
          <span class="text-display-lead">Building carbon overview</span>
        </h1>
        <p class="text-lead">{{ projectLine }}</p>
        <div class="project-actions">
          <q-btn unelevated no-caps class="btn-secondary" label="Back to the demo" to="/demo" />
        </div>
      </section>

      <!-- The page's one set of hero cards: the figure alone, its unit opens the line -->
      <section class="grid-3-col" aria-label="Headline results">
        <div class="gbdi-hero-card gbdi-hero-card--green">
          <p class="gbdi-hero-card__number">{{ kg.format(overview.headline.whole_life) }}</p>
          <p class="gbdi-hero-card__text">kg CO₂e over the whole life cycle, modules A to C.<sup>1</sup></p>
        </div>
        <div class="gbdi-hero-card gbdi-hero-card--blue">
          <p class="gbdi-hero-card__number">{{ figure(overview.headline.per_m2_useful, one) }}</p>
          <p class="gbdi-hero-card__text">
            kg CO₂e per m² of useful floor area; {{ figure(overview.headline.per_m2_gross, one) }} per m² of
            gross floor area.<sup>1</sup>
          </p>
        </div>
        <div class="gbdi-hero-card gbdi-hero-card--purple">
          <p class="gbdi-hero-card__number">{{ figure(overview.headline.per_m2_useful_per_year, two) }}</p>
          <p class="gbdi-hero-card__text">
            kg CO₂e per m² of useful floor area and year, over
            {{ figure(overview.project.reference_study_period_years, kg) }} years.<sup>1</sup>
          </p>
        </div>
      </section>

      <section class="project-section">
        <h2 class="text-h3">Carbon by life-cycle stage</h2>
        <p class="u-text-muted">
          Module D is reported beside the total, never inside it: D1 {{ kg.format(overview.headline.module_d1) }}
          kg CO₂e, D2 {{ kg.format(overview.headline.module_d2) }} kg CO₂e.
        </p>
        <BarsWithTable
          :bars="overview.stages.map((s) => bar(s.key, s.label, s.gwp, s.share))"
          :rows="overview.stages"
          :columns="stageColumns"
          row-key="key"
          caption="kg CO₂e and share of the whole-life total, same values as the table."
          empty-label="No life-cycle results in this project."
        />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Carbon by building element</h2>
        <p class="u-text-muted">OpenBDF element classification, Tier 2, in classification order.</p>
        <BarsWithTable
          :bars="elementRows.map((e, i) => bar(e.element, e.element, e.gwp, e.share, i >= overview!.elements.length))"
          :rows="elementRows"
          :columns="elementColumns"
          row-key="element"
          caption="kg CO₂e and share of the whole-life total. Rows without an element code stay visible."
          empty-label="No classified building elements in this project."
        />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Life-cycle stage by building element</h2>
        <p class="u-text-muted">OpenBDF element classification, each split across its life cycle, in kg CO₂e.</p>
        <StageByElement :stages="overview.stages" :rows="overview.element_stages" />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Material hotspots</h2>
        <p class="u-text-muted">
          Ranked by whole-life carbon, across every material and EPD product of the bill of materials.
        </p>
        <BarsWithTable
          :bars="overview.material_hotspots.map((m) => bar(pairKey(m), m.material || m.epd_product, m.gwp))"
          :rows="overview.material_hotspots"
          :columns="hotspotColumns"
          :row-key="pairKey"
          caption="kg CO₂e over the whole life cycle, same values as the table."
          empty-label="No materials in this project."
        />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Data type profile</h2>
        <p class="u-text-muted">
          The seven types of construction product data of Regulation (EU) 2026/52.
          {{ WEIGHTING[overview.data_type_weighting] }}
        </p>
        <BarsWithTable
          :bars="overview.data_types.map((d) => shareBar(d.key, d.label, d.share, d.key === 'undeclared'))"
          :rows="overview.data_types"
          :columns="dataTypeColumns"
          row-key="key"
          caption="Share of the weighting basis, same values as the table."
          empty-label="Not computed for this project."
        />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Material hotspots by mass</h2>
        <p class="u-text-muted">Ranked by mass, across every material and EPD product of the bill of materials.</p>
        <BarsWithTable
          :bars="overview.mass_hotspots.map((m) => bar(pairKey(m), m.material || m.epd_product, m.mass_kg))"
          :rows="overview.mass_hotspots"
          :columns="massColumns"
          :row-key="pairKey"
          caption="kg, same values as the table."
          empty-label="No materials in this project."
        />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Project details</h2>
        <p class="u-text-muted">General Information, as declared. Choose the columns to compare.</p>
        <ProjectFieldsTable :fields="overview.project_fields" />
      </section>

      <section class="project-section">
        <h2 class="text-h3">Data checks</h2>
        <p class="u-text-muted">Each life-cycle module declared in scope, against the results present.</p>
        <ModuleChecks
          :checks="overview.module_checks"
          :rows-read="overview.rows_read"
          :declared-without-result="overview.modules_declared_without_result"
          :result-without-declaration="overview.modules_with_undeclared_result"
        />
      </section>

      <footer class="u-text-muted">
        <ol>
          <li>
            Project {{ overview.project.project_id }}, {{ overview.project.lcia_methodology }},
            {{ overview.project.lca_database }}, {{ overview.project.system_boundary }}. Computed from the
            OpenBDF export, {{ kg.format(overview.rows_read) }} bill of materials rows.
          </li>
        </ol>
      </footer>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { QTableColumn } from 'quasar';
import BarsWithTable from '@/components/BarsWithTable.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import type { Bar } from '@/components/RankedBars.vue';
import StageByElement from '@/components/StageByElement.vue';
import type {
  DataTypeShare,
  ElementTotal,
  MassHotspot,
  MaterialHotspot,
  StageTotal,
} from '@/api/overview';
import { useOverview } from '@/composables/useOverview';
import { figure, kg, materialName, one, percent, three, two, WEIGHTING } from '@/format';

const { overview, error } = useOverview();
const pairKey = (row: { material: string; epd_product: string }) => `${row.material}|${row.epd_product}`;

const projectLine = computed(() => {
  const project = overview.value?.project;
  return [
    project?.project_id,
    project?.country,
    project?.gross_floor_area_m2 ? `${kg.format(project.gross_floor_area_m2)} m² gross floor area` : null,
    project?.reference_study_period_years ? `${project.reference_study_period_years}-year study period` : null,
  ]
    .filter(Boolean)
    .join(', ');
});

const gwpColumn = { label: 'GWP (kg CO₂e)', field: 'gwp', format: (v: number) => kg.format(v), align: 'right' } as const;
const shareColumn = { label: 'Share', field: 'share', format: (v: number) => percent.format(v), align: 'right' } as const;

const stageColumns: QTableColumn<StageTotal>[] = [
  { name: 'stage', label: 'Stage', field: 'label', align: 'left' },
  { name: 'gwp', ...gwpColumn },
  { name: 'share', ...shareColumn },
];
const elementColumns: QTableColumn<ElementTotal>[] = [
  { name: 'element', label: 'Element', field: 'element', align: 'left' },
  { name: 'gwp', ...gwpColumn },
  { name: 'share', ...shareColumn },
];
const hotspotColumns: QTableColumn<MaterialHotspot>[] = [
  { name: 'material', label: 'Material', field: 'material', format: materialName, align: 'left' },
  { name: 'epd', label: 'EPD product', field: 'epd_product', align: 'left' },
  { name: 'gwp', ...gwpColumn },
  { name: 'mass', label: 'Mass (kg)', field: 'mass_kg', format: (v: number) => kg.format(v), align: 'right' },
  { name: 'share', ...shareColumn },
  {
    name: 'intensity',
    label: 'kg CO₂e per kg',
    field: 'gwp_per_kg',
    format: (v: number | null) => figure(v, three),
    align: 'right',
  },
];
const massColumns: QTableColumn<MassHotspot>[] = [
  { name: 'material', label: 'Material', field: 'material', format: materialName, align: 'left' },
  { name: 'epd', label: 'EPD product', field: 'epd_product', align: 'left' },
  { name: 'mass', label: 'Mass (kg)', field: 'mass_kg', format: (v: number) => kg.format(v), align: 'right' },
  { name: 'share', label: 'Share of mass', field: 'share_of_mass', format: (v: number) => percent.format(v), align: 'right' },
];
const dataTypeColumns: QTableColumn<DataTypeShare>[] = [
  { name: 'type', label: 'Data type', field: 'label', align: 'left' },
  { name: 'share', ...shareColumn },
];


// Charts and tables read the same backend rows, in the backend's order.
const elementRows = computed(() =>
  overview.value === null
    ? []
    : [...overview.value.elements, overview.value.other_classified, overview.value.not_classified],
);
const bar = (key: string, label: string, value: number, share?: number, muted = false): Bar => ({
  key,
  label,
  value,
  display: share === undefined ? kg.format(value) : `${kg.format(value)}, ${percent.format(share)}`,
  muted,
});
const shareBar = (key: string, label: string, share: number, muted: boolean): Bar => ({
  key,
  label,
  value: share,
  display: percent.format(share),
  muted,
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.project-actions {
  display: flex;
  gap: tokens.$spacing-sm;
}

.project-section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
}

.project-section > h2,
.project-section > p {
  margin: 0;
}
</style>

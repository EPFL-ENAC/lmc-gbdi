<template>
  <!-- Sheet, for two buildings: one drawing sheet, the title block naming both, the
       figures in one table with their difference, then each panel drawn twice on the
       shared hairline grid, A on the left in green and B on the right in blue. -->
  <q-page class="sheet-page">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Loading both buildings…</p>

    <article v-else class="sheet">
      <header class="sheet__title">
        <div>
          <h1 class="sheet__name">{{ projectName(a) }} and {{ projectName(b) }}</h1>
          <p class="sheet__subtitle">Building carbon, compared</p>
        </div>
        <table class="sheet__block">
          <thead>
            <tr>
              <th scope="col" />
              <th v-for="side in sides" :key="side.key" scope="col">
                <span class="sheet__swatch" :class="`sheet__swatch--${side.key}`" />{{ projectName(side.o) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in titleRows" :key="row.label">
              <th scope="row">{{ row.label }}</th>
              <td v-for="side in sides" :key="side.key">{{ row.value(side.o) }}</td>
            </tr>
          </tbody>
        </table>
      </header>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Key figures, per m² of gross floor area</h2>
        <table class="sheet__figures">
          <thead>
            <tr>
              <th scope="col">Figure</th>
              <th v-for="side in sides" :key="side.key" scope="col" class="num">
                <span class="sheet__swatch" :class="`sheet__swatch--${side.key}`" />{{ projectName(side.o) }}
              </th>
              <th scope="col" class="num">Difference, B − A</th>
              <th scope="col" class="num">B / A</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in figureRows" :key="row.label">
              <th scope="row">{{ row.label }}</th>
              <td class="num sheet__big">{{ show(row.a, row.format) }}</td>
              <td class="num sheet__big">{{ show(row.b, row.format) }}</td>
              <td class="num">{{ row.a === null || row.b === null ? '–' : signed(row.b - row.a, row.format) }}</td>
              <td class="num">{{ row.a === null || row.b === null || row.a <= 0 ? '–' : percent.format(row.b / row.a) }}</td>
            </tr>
          </tbody>
        </table>
        <p class="sheet__note">
          kg CO₂e per m² unless stated. Module D1 lies outside the whole-life total. Not declared: no gross floor area.
        </p>
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Life-cycle stages</h2>
        <PairedBars :rows="stageRows" :a-label="projectName(a)" :b-label="projectName(b)" unit="kg CO₂e per m²" caption="Below zero: carbon stored or credited." />
      </section>

      <div class="sheet__pair">
        <section v-for="side in sides" :key="side.key" class="sheet__panel">
          <h2 class="sheet__panel-title">
            <span class="sheet__swatch" :class="`sheet__swatch--${side.key}`" />Element by stage, {{ projectName(side.o) }}
          </h2>
          <StageMatrix :stages="side.o.stages" :rows="side.o.element_stages" />
          <p class="sheet__note">
            Absolute kg CO₂e for {{ figure(side.o.project.gross_floor_area_m2, kg) }} m². Not classified:
            {{ kg.format(side.o.not_classified.gwp) }} kg CO₂e, {{ percent.format(side.o.not_classified.share) }} of the total.
          </p>
        </section>
      </div>

      <div class="sheet__pair">
        <section v-for="side in sides" :key="side.key" class="sheet__panel" :class="`sheet__side--${side.key}`">
          <h2 class="sheet__panel-title">
            <span class="sheet__swatch" :class="`sheet__swatch--${side.key}`" />Mass against carbon, {{ projectName(side.o) }}
          </h2>
          <IntensityPlot :hotspots="side.o.material_hotspots" />
        </section>
      </div>

      <div class="sheet__pair">
        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Materials by OpenBDF class</h2>
          <PairedBars :rows="classCarbon" :a-label="projectName(a)" :b-label="projectName(b)" unit="kg CO₂e per m²" caption="Whole-life carbon of each class." />
        </section>
        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Data types</h2>
          <PairedBars :rows="dataRows" :a-label="projectName(a)" :b-label="projectName(b)" unit="Share" :format="percent" :caption="`${WEIGHTING[a.data_type_weighting]} ${WEIGHTING[b.data_type_weighting]}`" />
        </section>
      </div>
    </article>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import type { Overview } from '@/api/overview';
import IntensityPlot from '@/components/IntensityPlot.vue';
import PairedBars from '@/components/PairedBars.vue';
import StageMatrix from '@/components/StageMatrix.vue';
import { pairRows, perM2, projectName } from '@/compare';
import { useOverviewPair } from '@/composables/useOverview';
import { figure, kg, one, percent, WEIGHTING } from '@/format';

const { a, b, error } = useOverviewPair();

const sides = computed(() =>
  a.value && b.value
    ? [
        { key: 'a', o: a.value },
        { key: 'b', o: b.value },
      ]
    : [],
);

const titleRows: { label: string; value: (o: Overview) => string }[] = [
  { label: 'Project', value: (o) => o.project.project_id ?? 'not declared' },
  { label: 'Country', value: (o) => o.project.country ?? 'not declared' },
  { label: 'Gross floor area', value: (o) => `${figure(o.project.gross_floor_area_m2, kg)} m²` },
  { label: 'Study period', value: (o) => `${figure(o.project.reference_study_period_years, kg)} years` },
  { label: 'Method', value: (o) => o.project.lcia_methodology ?? 'not declared' },
];

const show = (value: number | null, format: Intl.NumberFormat) => figure(value, format);
const signed = (value: number, format: Intl.NumberFormat) => `${value > 0 ? '+' : ''}${format.format(value)}`;

// Rows read is a count, not per m²: it says how detailed each bill of materials is.
const figureRows = computed(() => {
  if (!a.value || !b.value) return [];
  const row = (label: string, value: (o: Overview) => number | null, format: Intl.NumberFormat = one) => ({
    label,
    a: value(a.value!),
    b: value(b.value!),
    format,
  });
  return [
    row('Whole life (A–C)', (o) => perM2(o, o.headline.whole_life)),
    row('Upfront (A1–A5)', (o) => perM2(o, o.headline.upfront)),
    row('Use (B1–B8)', (o) => perM2(o, o.stages.find((s) => s.key === 'b1_b8')?.gwp ?? 0)),
    row('End of life (C1–C4)', (o) => perM2(o, o.stages.find((s) => s.key === 'c1_c4')?.gwp ?? 0)),
    row('Module D1', (o) => perM2(o, o.headline.module_d1)),
    row('Mass, kg per m²', (o) => perM2(o, o.total_mass_kg), kg),
    row('Bill-of-materials lines read', (o) => o.rows_read, kg),
  ];
});

const pair = <T,>(pick: (o: Overview) => T[], label: (r: T) => string, value: (r: T) => number) =>
  computed<ComparedRow[]>(() => (a.value && b.value ? pairRows(a.value, b.value, pick, label, value) : []));

const stageRows = pair((o) => o.stages, (s) => s.label, (s) => s.gwp);
const classCarbon = pair((o) => o.material_classes, (m) => m.label, (m) => m.gwp);

// Shares, not per m²: the data type profile is already relative.
const dataRows = computed<ComparedRow[]>(() => {
  if (!a.value || !b.value) return [];
  const share = (o: Overview, key: string) => o.data_types.find((d) => d.key === key)?.share ?? 0;
  const types = new Map([...a.value.data_types, ...b.value.data_types].map((d) => [d.key, d.label]));
  return [...types].map(([key, label]) => ({ label, a: share(a.value!, key), b: share(b.value!, key) }));
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

// The same desk and sheet as the single-building Sheet.
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

// The title block, one column per building.
.sheet__block {
  align-self: flex-end;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
}

.sheet__block th,
.sheet__block td {
  padding: tokens.$spacing-xxs tokens.$spacing-lg;
  border-left: tokens.$border-width solid tokens.$color-border-control;
  text-align: left;
}

.sheet__block th {
  font-size: tokens.$text-size-xs;
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
}

.sheet__figures {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}

.sheet__figures th,
.sheet__figures td {
  padding: tokens.$spacing-sm tokens.$spacing-md;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
}

.sheet__figures thead th {
  font-weight: tokens.$text-weight-medium;
}

.sheet__figures tbody th {
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
}

.sheet__figures .num {
  text-align: right;
  white-space: nowrap;
}

.sheet__big {
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-lg;
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
  min-width: 0;
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

.sheet__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
}

.sheet__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.sheet__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
}

// The intensity plot draws in the primary green; B's points take B's blue.
.sheet__side--a :deep(.intensity__point circle) {
  fill: var(--gbdi-dataviz-green-1);
}

.sheet__side--b :deep(.intensity__point circle) {
  fill: var(--gbdi-dataviz-blue-2);
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

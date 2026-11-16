<template>
  <!-- The one view of a building (globalbuildingdatainitiative/org#97), a drawing sheet
       read top to bottom: what the project is, then its mass, its emissions, its
       materials, and how far its data can be trusted. -->
  <q-page class="sheet-page">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <article v-else class="sheet">
      <!-- Every absolute figure of the page on one basis, and every element and material
           under one naming, both chosen in the building bar. -->
      <Teleport defer to="#basis-control">
        <!-- org#102: the basis is the main choice, labelled and boxed; the naming is a
             secondary checkbox beside it. -->
        <div class="sheet__show" role="group" aria-labelledby="sheet-show-label">
          <span id="sheet-show-label" class="sheet__show-label">Show</span>
          <q-btn-toggle
            v-model="basis"
            :options="basisOptions"
            no-caps
            unelevated
            dense
            toggle-color="primary"
            color="white"
            text-color="dark"
            class="sheet__basis"
          />
        </div>
        <q-checkbox v-model="openbdfNames" label="Common OpenBDF names" dense />
      </Teleport>
      <!-- Below 600 px the controls above fold behind the bar's Display button: the
           button still names the current basis. -->
      <Teleport v-if="$q.screen.lt.sm" defer to="#display-summary">{{
        `: ${overview.bases.find((b) => b.key === basis)?.label}`
      }}</Teleport>
      <Teleport defer to="#sheet-toc">
        <SheetToc />
      </Teleport>

      <!-- Project info -->
      <header id="project-info" class="sheet__title">
        <div>
          <h1 class="sheet__name">{{ overview.project.project_name ?? 'Unnamed project' }}</h1>
          <p class="sheet__subtitle">Building carbon overview<DraftBadge :building-id="Number($route.params.id)" /></p>
        </div>
        <!-- org#106: one cell per field. The five method fields decide whether two
             projects compare, so they are tinted and tagged. -->
        <dl class="info-grid">
          <!-- org#108: the id the dashboard gives, beside the Project ID the workbook declares. -->
          <div class="info-cell">
            <dt class="info-cell__label">GBDI ID</dt>
            <dd class="info-cell__value">{{ overview.gbdi_id ?? 'Not assigned' }}</dd>
          </div>
          <div
            v-for="field in overview.title_block"
            :key="field.code"
            class="info-cell"
            :class="{ 'info-cell--scope': field.scope }"
          >
            <dt class="info-cell__label">
              {{ field.label }}
              <span v-if="field.scope" class="info-cell__tag">Scope</span>
            </dt>
            <dd class="info-cell__value">
              {{
                field.code === 'lca_cycle_system_boundary'
                  ? (overview.project.declared_scope ?? NOT_DECLARED)
                  : fieldText(field.value, field.unit)
              }}
            </dd>
          </div>
        </dl>
      </header>

      <section class="sheet__panel" aria-label="Headline results">
        <div class="grid-3-col">
          <BigNumber :value="num.format(overview.headline.whole_life)" tone="green">
            {{ units.carbon }}, total {{ overview.headline.scope }}.
          </BigNumber>
          <BigNumber :value="num.format(overview.headline.upfront)" tone="blue">
            {{ units.carbon }} before the building is used, A1–A5:
            {{ percent.format(overview.headline.upfront_share) }} of the total.
          </BigNumber>
          <BigNumber v-if="showModuleD(overview.headline)" :value="num.format(overview.headline.module_d)" tone="purple">
            {{ units.carbon }}, module D, outside the total: D1, material recovery (reuse, recycling, energy
            recovery), {{ num.format(overview.headline.module_d1) }}; D2, exported utilities,
            {{ num.format(overview.headline.module_d2) }}.
          </BigNumber>
        </div>
        <!-- org#107: the boundary the workbook declares, next to the modules it computes. -->
        <p class="scope-chip">Scope {{ overview.project.declared_scope ?? NOT_DECLARED }}</p>
        <p class="sheet__note">
          Computed from the OpenBDF workbook, {{ kg.format(overview.rows_read) }} bill of materials rows, data from
          {{ overview.project.lca_database ?? 'an undeclared database' }}.
        </p>
      </section>

      <!-- Mass -->
      <section id="mass" class="sheet__panel">
        <div class="sheet__panel-head">
          <h2 class="sheet__panel-title">Building elements</h2>
          <q-btn-toggle
            v-model="measure"
            :options="MEASURES"
            aria-label="Element bars by"
            no-caps
            unelevated
            toggle-color="primary"
            color="white"
            text-color="dark"
            class="sheet__switch"
          />
        </div>
        <p class="u-text-muted">
          {{ num.format(overview.total_mass_kg) }} {{ units.mass }} of materials.
          {{ measure === 'mass' ? 'Mass' : 'Carbon' }} by {{ ELEMENTS_BY[naming] }}.
        </p>
        <BarsWithTable
          :bars="elementBars"
          :rows="elementRows"
          :columns="elementColumns"
          :row-key="(row: ElementTotal) => String(elementRows.indexOf(row))"
          :caption="
            measure === 'mass'
              ? `${units.mass} and share of the total mass. Rows without an element stay visible.`
              : `${units.carbon} and share of the total carbon. Rows without an element stay visible.`
          "
          empty-label="No classified building elements in this project."
        />
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Materials within the elements</h2>
        <p class="u-text-muted">The heaviest materials of each element, by mass.</p>
        <ElementMaterials :elements="view!.element_materials" :units="units" />
      </section>

      <!-- Emissions: the stages as a strip, then the same stages on a timeline. -->
      <section id="emissions" class="sheet__panel">
        <h2 class="sheet__panel-title">Life-cycle stages</h2>
        <LifeCycleStrip
          :stages="overview.stages"
          :whole-life="overview.headline.whole_life"
          :scope="overview.headline.scope"
          :module-d="showModuleD(overview.headline) ? overview.headline : null"
          :units="units"
        />
      </section>

      <section class="sheet__panel">
        <TimeSection :overview="overview" />
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Element by stage</h2>
        <StageMatrix
          :stages="overview.stages"
          :rows="view!.element_stages.map((e) => ({ ...e, key: e.element, label: e.element }))"
          :units="units"
          row-header="Element"
          empty-label="No classified building elements in this project."
        />
        <p class="sheet__note">
          Not classified: {{ num.format(view!.not_classified.gwp) }} {{ units.carbon }},
          {{ percent.format(view!.not_classified.share) }} of the total.
        </p>
      </section>

      <!-- Materials. The anchor sits before the component, whose root starts with comments. -->
      <span id="materials" class="sheet__anchor" />
      <MaterialWalls :overview="view!" />

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Cumulative carbon — top 10 materials</h2>
        <p class="u-text-muted">How much of the total the ten largest materials account for.</p>
        <CumulativeShare :hotspots="view!.material_hotspots" />
      </section>

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Materials, mass against carbon</h2>
        <IntensityPlot :hotspots="view!.material_hotspots" :units="units" />
      </section>

      <!-- Data quality -->
      <section id="data-quality" class="sheet__panel">
        <h2 class="sheet__panel-title">Data type profile</h2>
        <RankedBars :bars="dataTypeBars" :caption="weightingCaption(overview)" empty-label="Not computed." />
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
        <p class="u-text-muted">General Information, as declared. Choose the fields to show.</p>
        <ProjectFieldsTable :fields="overview.project_fields" />
      </section>
    </article>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { QTableColumn } from 'quasar';
import type { ElementTotal, Naming } from '@/api/overview';
import BarsWithTable from '@/components/BarsWithTable.vue';
import CumulativeShare from '@/components/CumulativeShare.vue';
import DraftBadge from '@/components/DraftBadge.vue';
import ElementMaterials from '@/components/ElementMaterials.vue';
import IntensityPlot from '@/components/IntensityPlot.vue';
import LifeCycleStrip from '@/components/LifeCycleStrip.vue';
import MaterialWalls from '@/components/MaterialWalls.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import BigNumber from '@/components/molecules/BigNumber.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import SheetToc from '@/components/SheetToc.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import StageMatrix from '@/components/StageMatrix.vue';
import TimeSection from '@/components/TimeSection.vue';
import { useOverview } from '@/composables/useOverview';
import { showModuleD } from '@/dataviz';
import { amount, fieldText, kg, NOT_DECLARED, percent, weightingCaption } from '@/format';

const { overview, error, basis, naming } = useOverview();
// Read only where the overview is loaded.
const units = computed(() => overview.value!.units);
const num = computed(() => amount(units.value));
const basisOptions = computed(() =>
  (overview.value?.bases ?? []).map((b) => ({
    label: b.label,
    value: b.key,
    disable: !b.available,
    attrs: { title: b.reason ?? undefined },
  })),
);

// The backend sends every element and material figure under both namings; the checkbox
// only picks one, so it needs no new request. A view has the top-level field names.
const ELEMENTS_BY: Record<Naming, string> = {
  openbdf: 'OpenBDF element, Tier 2, in classification order',
  custom: "the project's own element class, in label order",
};
// Checked is the OpenBDF classification, unchecked the project's custom names.
const openbdfNames = computed({
  get: () => naming.value === 'openbdf',
  set: (on: boolean) => (naming.value = on ? 'openbdf' : 'custom'),
});
const view = computed(() => (overview.value === null ? null : { ...overview.value, ...overview.value.namings[naming.value] }));

// Chart and table read the same backend rows, in the backend's order.
const elementRows = computed(() =>
  view.value === null ? [] : [...view.value.elements, view.value.other_classified, view.value.not_classified],
);
type Measure = 'carbon' | 'mass';
const MEASURES: { label: string; value: Measure }[] = [
  { label: 'Carbon', value: 'carbon' },
  { label: 'Mass', value: 'mass' },
];
const measure = ref<Measure>('carbon');
const elementBars = computed<Bar[]>(() =>
  elementRows.value.map((e, i) => {
    const [value, share] = measure.value === 'mass' ? [e.mass_kg, e.share_of_mass] : [e.gwp, e.share];
    return {
      key: String(i),
      label: e.element,
      value,
      display: share === null ? num.value.format(value) : `${num.value.format(value)}, ${percent.format(share)}`,
      missing: e === view.value!.not_classified,
    };
  }),
);
const shareText = (v: number | null) => (v === null ? 'no mass declared' : percent.format(v));
const elementColumns = computed<QTableColumn<ElementTotal>[]>(() => [
  { name: 'element', label: 'Element', field: 'element', align: 'left' },
  { name: 'gwp', label: `GWP (${units.value.carbon})`, field: 'gwp', format: (v: number) => num.value.format(v), align: 'right' },
  { name: 'share', label: 'Share of the carbon', field: 'share', format: (v: number) => percent.format(v), align: 'right' },
  { name: 'mass_kg', label: `Mass (${units.value.mass})`, field: 'mass_kg', format: (v: number) => num.value.format(v), align: 'right' },
  { name: 'share_of_mass', label: 'Share of the mass', field: 'share_of_mass', format: shareText, align: 'right' },
]);

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

// org#101: a table of contents stop lands below the sticky header. SheetToc keeps the
// variable at the header's height; without script the fallback applies.
.sheet [id] {
  scroll-margin-top: calc(var(--sheet-header-h, 9rem) + #{tokens.$spacing-sm});
}

.sheet__anchor {
  display: block;
  border-top: 0; // not a panel: no rule of its own above the materials
}

.sheet__name {
  margin: 0;
  font-size: tokens.$text-size-display-md;
}

.sheet__show {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: tokens.$spacing-sm;
}

.sheet__show-label {
  font-size: tokens.$text-size-xs;
  font-weight: 700;
  letter-spacing: tokens.$text-letter-spacing-label;
  text-transform: uppercase;
  color: tokens.$color-text-muted;
}

.sheet__basis {
  flex-wrap: wrap;
  border: tokens.$border-width solid tokens.$color-border-control;
  border-radius: tokens.$radius-default;
}

.sheet__panel-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: tokens.$spacing-md;
}

.sheet__switch {
  border: tokens.$border-width solid tokens.$color-border;
}

// A grid of labelled cells; the gap on the border colour draws the rules and fills
// the empty end of the last row.
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
  gap: tokens.$border-width;
  margin: 0;
  background: tokens.$color-border;
  border: tokens.$border-width solid tokens.$color-border;
}

.info-cell {
  padding: tokens.$spacing-sm tokens.$spacing-md;
  background: tokens.$color-surface;
}

.info-cell--scope {
  background: tokens.$color-surface-highlight;
}

.info-cell__label {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  letter-spacing: tokens.$text-letter-spacing-label;
  text-transform: uppercase;
  color: tokens.$color-text-muted;
}

.info-cell__tag {
  padding: 0 tokens.$spacing-xs;
  border-radius: tokens.$radius-xs;
  background: tokens.$color-data-present;
  color: tokens.$color-primary-strong;
  font-weight: 600;
}

.info-cell__value {
  margin: 0;
}

.scope-chip {
  align-self: flex-start;
  width: fit-content;
  margin: tokens.$spacing-md 0 0;
  padding: tokens.$spacing-xs tokens.$spacing-md;
  border-radius: tokens.$radius-pill;
  background: tokens.$color-surface-highlight;
  color: tokens.$color-primary-strong;
  font-size: tokens.$text-size-sm;
  font-weight: 600;
}

.sheet__subtitle {
  margin: 0;
  color: tokens.$color-text-lead;
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-md;
}
</style>

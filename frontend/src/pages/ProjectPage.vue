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
        <q-btn-toggle
          v-model="basis"
          :options="basisOptions"
          aria-label="Figures per"
          no-caps
          unelevated
          dense
          toggle-color="primary"
          color="white"
          text-color="dark"
        />
        <q-btn-toggle
          v-model="naming"
          :options="NAMINGS"
          aria-label="Element and material names"
          no-caps
          unelevated
          dense
          toggle-color="primary"
          color="white"
          text-color="dark"
          class="sheet__naming"
        />
      </Teleport>

      <!-- Project info -->
      <header class="sheet__title">
        <div>
          <h1 class="sheet__name">{{ overview.project.project_name ?? 'Unnamed project' }}</h1>
          <p class="sheet__subtitle">Building carbon overview</p>
        </div>
        <dl class="sheet__block">
          <div v-for="field in overview.title_block" :key="field.code">
            <dt>{{ field.label }}</dt>
            <dd>{{ fieldText(field.value) }}</dd>
          </div>
        </dl>
      </header>

      <section class="sheet__panel" aria-label="Headline results">
        <div class="grid-3-col">
          <BigNumber :value="num.format(overview.headline.whole_life)" tone="green">
            {{ units.carbon }}, {{ overview.headline.scope }}.
          </BigNumber>
          <BigNumber :value="num.format(overview.headline.upfront)" tone="blue">
            {{ units.carbon }} before the building is used, A1–A5:
            {{ percent.format(overview.headline.upfront_share) }} of the whole life.
          </BigNumber>
          <BigNumber :value="num.format(overview.headline.module_d1)" tone="purple">
            {{ units.carbon }} of benefits from reuse and recycling, module D1, outside the total.
          </BigNumber>
        </div>
        <p class="sheet__note">
          Computed from the OpenBDF workbook, {{ kg.format(overview.rows_read) }} bill of materials rows, data from
          {{ overview.project.lca_database ?? 'an undeclared database' }}.
        </p>
      </section>

      <!-- Mass -->
      <section class="sheet__panel">
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
          {{ measure === 'mass' ? 'Mass' : 'Whole-life carbon' }} by {{ ELEMENTS_BY[naming] }}.
        </p>
        <BarsWithTable
          :bars="elementBars"
          :rows="elementRows"
          :columns="elementColumns"
          :row-key="(row: ElementTotal) => String(elementRows.indexOf(row))"
          :caption="
            measure === 'mass'
              ? `${units.mass} and share of the total mass. Rows without an element stay visible.`
              : `${units.carbon} and share of the whole-life total. Rows without an element stay visible.`
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
      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Life-cycle stages</h2>
        <LifeCycleStrip
          :stages="overview.stages"
          :whole-life="overview.headline.whole_life"
          :module-d="overview.headline.module_d1"
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

      <!-- Materials -->
      <MaterialWalls :overview="view!" />

      <section class="sheet__panel">
        <h2 class="sheet__panel-title">Materials, mass against carbon</h2>
        <IntensityPlot :hotspots="view!.material_hotspots" :units="units" />
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
import ElementMaterials from '@/components/ElementMaterials.vue';
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
import { amount, fieldText, kg, percent, WEIGHTING } from '@/format';

const { overview, error, basis } = useOverview();
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

// The backend sends every element and material figure under both namings; the toggle
// only picks one, so it needs no new request. A view has the top-level field names.
const NAMINGS: { label: string; value: Naming }[] = [
  { label: 'OpenBDF classification', value: 'openbdf' },
  { label: 'Custom names', value: 'custom' },
];
const ELEMENTS_BY: Record<Naming, string> = {
  openbdf: 'OpenBDF element, Tier 2, in classification order',
  custom: "the project's own element class, in label order",
};
const naming = ref<Naming>('openbdf');
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

.sheet__name {
  margin: 0;
  font-size: tokens.$text-size-display-md;
}

.sheet__naming {
  margin-left: tokens.$spacing-md;
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

.sheet__subtitle {
  margin: 0;
  color: tokens.$color-text-lead;
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-md;
}
</style>

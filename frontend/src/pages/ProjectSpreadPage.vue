<template>
  <!-- Variant 1, "Spread": the brand book's own page grid (p.6–26). A narrow column
       explains, the wide column shows, a hairline and a caption close each spread. -->
  <q-page class="spread">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <template v-else>
      <header class="spread__head">
        <h1>
          {{ overview.project.project_name ?? 'Unnamed project' }}<br />
          <span class="text-display-lead">Building carbon overview</span>
        </h1>
      </header>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Whole life</h2>
          <p>
            Modules A to C over a {{ figure(overview.project.reference_study_period_years, kg) }}-year study period.
            Module D, the benefits beyond the building's life, is reported beside the total, never in it.
          </p>
        </div>
        <div class="spread__main grid-3-col">
          <div class="gbdi-hero-card gbdi-hero-card--green">
            <p class="gbdi-hero-card__number">{{ kg.format(overview.headline.whole_life) }}</p>
            <p class="gbdi-hero-card__text">kg CO₂e over the whole life cycle.</p>
          </div>
          <div class="gbdi-hero-card gbdi-hero-card--blue">
            <p class="gbdi-hero-card__number">{{ figure(overview.headline.per_m2_useful, one) }}</p>
            <p class="gbdi-hero-card__text">kg CO₂e per m² of useful floor area.</p>
          </div>
          <div class="gbdi-hero-card gbdi-hero-card--purple">
            <p class="gbdi-hero-card__number">{{ kg.format(overview.headline.upfront) }}</p>
            <p class="gbdi-hero-card__text">kg CO₂e upfront, before the building is used (A1–A5).</p>
          </div>
        </div>
        <p class="spread__caption">{{ sourceLine }}</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Life-cycle stages</h2>
          <p>Where the carbon falls in time, from making the materials to taking the building down.</p>
        </div>
        <div class="spread__main">
          <LifeCycleStrip
            :stages="overview.stages"
            :whole-life="overview.headline.whole_life"
            :module-d="overview.headline.module_d1"
          />
        </div>
        <p class="spread__caption">kg CO₂e and share of the whole-life total. Dashed: module D, on the same scale.</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Building elements</h2>
          <p>The parts of the building that carry the carbon, in OpenBDF Tier 2 order.</p>
        </div>
        <div class="spread__main">
          <RankedBars :bars="elementBars" caption="kg CO₂e and share of the whole-life total." empty-label="No classified elements." />
          <details class="spread__details">
            <summary>Show each element by life-cycle stage</summary>
            <StageByElement :stages="overview.stages" :rows="overview.element_stages" />
          </details>
        </div>
        <p class="spread__caption">Rows without an element code stay visible as "Not classified".</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Materials</h2>
          <p>The materials that weigh most in carbon, then in mass. The two lists rarely agree.</p>
        </div>
        <div class="spread__main grid-2-col">
          <RankedBars :bars="carbonBars" caption="By whole-life carbon, kg CO₂e." empty-label="No materials." />
          <RankedBars :bars="massBars" caption="By mass, kg." empty-label="No materials." />
        </div>
        <p class="spread__caption">Every material and EPD product of the bill of materials, top 10 of each.</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Data</h2>
          <p>What kind of data the materials rest on, and whether the declared scope matches the results.</p>
        </div>
        <div class="spread__main spread__stack">
          <RankedBars :bars="dataTypeBars" :caption="WEIGHTING[overview.data_type_weighting]" empty-label="Not computed." />
          <ModuleChecks
            :checks="overview.module_checks"
            :rows-read="overview.rows_read"
            :declared-without-result="overview.modules_declared_without_result"
            :result-without-declaration="overview.modules_with_undeclared_result"
          />
        </div>
        <p class="spread__caption">The seven data types of Regulation (EU) 2026/52; the modules in life-cycle order.</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Project</h2>
          <p>Everything General Information declares. Add the columns you need.</p>
        </div>
        <div class="spread__main">
          <ProjectFieldsTable :fields="overview.project_fields" />
        </div>
        <p class="spread__caption">Blank fields read "not declared".</p>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import LifeCycleStrip from '@/components/LifeCycleStrip.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import StageByElement from '@/components/StageByElement.vue';
import { useOverview } from '@/composables/useOverview';
import { figure, kg, one, percent, WEIGHTING } from '@/format';

const { overview, error } = useOverview();

const sourceLine = computed(() => {
  const p = overview.value?.project;
  return [`Project ${p?.project_id ?? 'without ID'}`, p?.lcia_methodology, p?.lca_database].filter(Boolean).join(', ');
});

const elementBars = computed<Bar[]>(() => {
  const o = overview.value;
  if (o === null) return [];
  return [...o.elements, o.other_classified, o.not_classified].map((e, i) => ({
    key: e.element,
    label: e.element,
    value: e.gwp,
    display: `${kg.format(e.gwp)} kg, ${percent.format(e.share)}`,
    muted: i >= o.elements.length,
  }));
});
const carbonBars = computed<Bar[]>(() =>
  (overview.value?.material_hotspots ?? []).map((m) => ({
    key: `${m.material}|${m.epd_product}`,
    label: m.material || m.epd_product,
    value: m.gwp,
    display: kg.format(m.gwp),
  })),
);
const massBars = computed<Bar[]>(() =>
  (overview.value?.mass_hotspots ?? []).map((m) => ({
    key: `${m.material}|${m.epd_product}`,
    label: m.material || m.epd_product,
    value: m.mass_kg,
    display: kg.format(m.mass_kg),
  })),
);
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

.spread {
  max-width: tokens.$layout-page-width;
  margin: 0 auto;
  padding: tokens.$spacing-page tokens.$spacing-lg;
}

.spread__head {
  margin-bottom: tokens.$spacing-page;
}

// The guideline grid: a quarter for words, three quarters for the visual.
.spread__section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 3fr);
  column-gap: tokens.$spacing-page;
  row-gap: tokens.$spacing-lg;
  margin-bottom: tokens.$spacing-page;
}

.spread__aside p {
  margin: 0;
  color: tokens.$color-text-muted;
}

.spread__title {
  margin: 0 0 tokens.$spacing-md;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.spread__stack {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-xl;
}

// The caption under a hairline, like the page footers of the guidelines.
.spread__caption {
  grid-column: 2;
  margin: 0;
  padding-top: tokens.$spacing-md;
  border-top: tokens.$border-width solid tokens.$color-border;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.spread__details {
  margin-top: tokens.$spacing-lg;
}

.spread__details summary {
  cursor: pointer;
  color: tokens.$color-text-link;
  text-decoration: underline;
  text-underline-offset: 0.125rem;
  margin-bottom: tokens.$spacing-lg;
}

@media (max-width: 1199px) {
  .spread__section {
    grid-template-columns: minmax(0, 1fr);
  }

  .spread__caption {
    grid-column: 1;
  }
}
</style>

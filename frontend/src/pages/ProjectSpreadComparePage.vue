<template>
  <!-- Spread, for two buildings: the same page grid, a narrow column that explains and a
       wide one that shows, but every figure per m² of gross floor area and every chart
       paired, A in green and B in blue. -->
  <q-page class="spread">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Loading both buildings…</p>

    <template v-else>
      <header class="spread__head">
        <h1>
          {{ projectName(a) }} and {{ projectName(b) }}<br />
          <span class="text-display-lead">Side by side, per m<sup>2</sup></span>
        </h1>
      </header>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Whole life</h2>
          <p>
            Modules A to C per m² of gross floor area, the one basis on which two buildings of different sizes compare.
            Module D stays beside the total.
          </p>
        </div>
        <div class="spread__main grid-2-col">
          <BigNumber
            v-for="side in sides"
            :key="side.key"
            :label="projectName(side.o)"
            :value="figure(perM2(side.o, side.o.headline.whole_life), kg)"
            :tone="side.tone"
          >
            kg CO₂e per m² over the whole life; {{ figure(perM2(side.o, side.o.headline.upfront), kg) }} of it upfront
            (A1–A5).
          </BigNumber>
        </div>
        <p class="spread__caption">{{ ratioLine }}</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Life-cycle stages</h2>
          <p>Where each building's carbon falls in time, from making the materials to taking it down.</p>
        </div>
        <div class="spread__main">
          <PairedBars :rows="stageRows" :a-label="a.code" :b-label="b.code" unit="kg CO₂e per m²" caption="" />
        </div>
        <p class="spread__caption">Below zero: carbon stored or credited, most often biogenic carbon in timber.</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Building elements</h2>
          <p>The parts that carry the carbon, in OpenBDF Tier 2 order, then what neither classifies.</p>
        </div>
        <div class="spread__main">
          <PairedBars :rows="elementRows" :a-label="a.code" :b-label="b.code" unit="kg CO₂e per m²" caption="" />
        </div>
        <p class="spread__caption">Rows without an element code stay visible as "Not classified".</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Materials</h2>
          <p>
            Custom material names never match across projects; the OpenBDF material class does. Carbon and mass rarely
            rank the same.
          </p>
        </div>
        <div class="spread__main grid-2-col">
          <PairedBars :rows="classCarbon" :a-label="a.code" :b-label="b.code" unit="kg CO₂e per m²" caption="By whole-life carbon." />
          <PairedBars :rows="classMass" :a-label="a.code" :b-label="b.code" unit="kg per m²" caption="By mass." />
        </div>
        <p class="spread__caption">Every line of both bills of materials, grouped by OpenBDF class.</p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Data</h2>
          <p>What kind of data each bill of materials rests on. A comparison is only as firm as its softer side.</p>
        </div>
        <div class="spread__main">
          <p v-if="noDataTypes(a, b)">{{ NO_DATA_TYPES_SENTENCE }}</p>
          <PairedBars v-else :rows="dataRows" :a-label="a.code" :b-label="b.code" unit="Share" :format="percent" caption="" />
        </div>
        <p v-if="!noDataTypes(a, b)" class="spread__caption">
          {{ [...new Set([WEIGHTING[a.data_type_weighting], WEIGHTING[b.data_type_weighting]])].join(' ') }}
        </p>
      </section>

      <section class="spread__section">
        <div class="spread__aside">
          <h2 class="spread__title">Project</h2>
          <p>What General Information declares, field by field. Differences in scope show here first.</p>
        </div>
        <div class="spread__main">
          <table class="spread__fields">
            <thead>
              <tr>
                <th scope="col">Field</th>
                <th scope="col"><span class="spread__swatch spread__swatch--a" />{{ projectName(a) }}</th>
                <th scope="col"><span class="spread__swatch spread__swatch--b" />{{ projectName(b) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in differing" :key="row.code">
                <th scope="row">{{ row.label }}</th>
                <td>{{ row.a }}</td>
                <td>{{ row.b }}</td>
              </tr>
            </tbody>
          </table>
          <details class="spread__more">
            <summary>Show all {{ fieldRows.length }} fields</summary>
            <table class="spread__fields">
              <tbody>
                <tr v-for="row in fieldRows" :key="row.code">
                  <th scope="row">{{ row.label }}</th>
                  <td>{{ row.a }}</td>
                  <td>{{ row.b }}</td>
                </tr>
              </tbody>
            </table>
          </details>
        </div>
        <p class="spread__caption">The fields the two buildings declare differently; the rest are the same.</p>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import BigNumber from '@/components/molecules/BigNumber.vue';
import PairedBars from '@/components/PairedBars.vue';
import { NO_DATA_TYPES_SENTENCE, noDataTypes, pairRows, perM2, projectName } from '@/compare';
import { useOverviewPair } from '@/composables/useOverview';
import { fieldText, figure, kg, percent, WEIGHTING } from '@/format';

const { a, b, error } = useOverviewPair();

const sides = computed(() =>
  a.value && b.value
    ? [
        { key: 'a', tone: 'green' as const, o: a.value },
        { key: 'b', tone: 'blue' as const, o: b.value },
      ]
    : [],
);

const ratioLine = computed(() => {
  if (!a.value || !b.value) return '';
  const ra = perM2(a.value, a.value.headline.whole_life);
  const rb = perM2(b.value, b.value.headline.whole_life);
  if (ra === null || rb === null || ra === 0) return 'A gross floor area is missing: the two cannot be set per m².';
  return `Per m², ${projectName(b.value)} emits ${percent.format(rb / ra)} of what ${projectName(a.value)} emits over its whole life.`;
});

const pair = <T,>(pick: (o: NonNullable<typeof a.value>) => T[], label: (r: T) => string, value: (r: T) => number) =>
  computed<ComparedRow[]>(() => (a.value && b.value ? pairRows(a.value, b.value, pick, label, value) : []));

const stageRows = pair((o) => o.stages, (s) => s.label, (s) => s.gwp);
const elementRows = pair((o) => [...o.elements, o.other_classified, o.not_classified], (e) => e.element, (e) => e.gwp);
const classCarbon = pair((o) => o.material_classes, (m) => m.label, (m) => m.gwp);
const classMass = pair((o) => o.material_classes, (m) => m.label, (m) => m.mass_kg);

// Shares, not per m²: the data type profile is already relative.
const dataRows = computed<ComparedRow[]>(() => {
  if (!a.value || !b.value) return [];
  const share = (o: typeof a.value, key: string) => o.data_types.find((d) => d.key === key)?.share ?? 0;
  const types = new Map([...a.value.data_types, ...b.value.data_types].map((d) => [d.key, d.label]));
  return [...types].map(([key, label]) => ({ label, a: share(a.value!, key), b: share(b.value!, key) }));
});

const fieldRows = computed(() => {
  if (!a.value || !b.value) return [];
  const inB = new Map(b.value.project_fields.map((f) => [f.code, f.value]));
  return a.value.project_fields.map((f) => ({
    code: f.code,
    label: f.label,
    a: fieldText(f.value),
    b: fieldText(inB.get(f.code) ?? null),
  }));
});
const differing = computed(() => fieldRows.value.filter((row) => row.a !== row.b));
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

// SK Modernist has no ² glyph: a sized-down 2 instead.
.spread__head sup {
  font-size: 0.45em;
  line-height: 0;
}

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


.spread__caption {
  grid-column: 2;
  margin: 0;
  padding-top: tokens.$spacing-md;
  border-top: tokens.$border-width solid tokens.$color-border;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.spread__fields {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
}

.spread__fields th,
.spread__fields td {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
  vertical-align: top;
}

.spread__fields thead th,
.spread__fields tbody th {
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
}

.spread__more {
  margin-top: tokens.$spacing-lg;
}

.spread__more summary {
  cursor: pointer;
  color: tokens.$color-text-link;
  text-decoration: underline;
  text-underline-offset: 0.125rem;
  margin-bottom: tokens.$spacing-md;
}

.spread__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
}

.spread__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.spread__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
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

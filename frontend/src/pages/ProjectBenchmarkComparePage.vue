<template>
  <!-- Benchmark, for two buildings: both placed on the same published scales, A in green
       and B in blue, then the elements that would move each, then whether each scope is
       complete enough for the rating to hold. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Loading both buildings…</p>

    <template v-else>
      <header>
        <h1>
          {{ projectName(a) }} and {{ projectName(b) }}<br />
          <span class="text-display-lead">On the same published scales</span>
        </h1>
        <p class="text-lead">
          Reference points, not a compliance check: each scale counts its own modules over its own floor area, the same
          for both buildings.
        </p>
      </header>

      <section v-for="scale in placedScales" :key="scale.key" class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">{{ scale.name }}</h2>
          <p v-for="side in scale.sides" :key="side.key" class="bench__verdict">
            <span class="bench__swatch" :class="`bench__swatch--${side.key}`" />{{ side.name }}:
            <strong>{{ side.benchmark?.band ?? 'not placed' }}</strong>
            <template v-if="side.benchmark && side.benchmark.value !== null">
              at {{ one.format(side.benchmark.value) }} kg CO₂e per m²
            </template>
          </p>
          <p class="bench__scope">{{ bothScope(scale.scope) }}</p>
          <p class="bench__source">
            Source: <a class="link" :href="scale.source_url" target="_blank" rel="noopener">{{ scale.source }}</a>
          </p>
        </div>

        <!-- The scale once, each building marked on it. -->
        <RatingLabel v-if="scale.key === 'leti'" :benchmark="scale" :marks="scale.marks" />
        <CeilingRuler v-else :benchmark="scale" :marks="scale.marks" />
      </section>

      <!-- A scale that places neither building is one line, not an empty chart. -->
      <p v-for="scale in unplacedScales" :key="scale.key" class="bench bench__none">
        <strong>{{ scale.name }}</strong>: neither building is placed;
        {{ scale.basis === 'per_m2_useful' ? 'neither declares a useful floor area' : 'neither declares a gross floor area' }}.
      </p>

      <section class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">What would move them</h2>
          <p class="bench__scope">
            A band moves with the elements that carry the most carbon. Per m² of gross floor area, element by element,
            the gap between the two buildings shows where.
          </p>
        </div>
        <PairedBars
          :rows="elementRows"
          :a-label="a.code"
          :b-label="b.code"
          unit="kg CO₂e per m²"
          caption="OpenBDF Tier 2 elements, whole life, then what neither classifies."
        />
      </section>

      <section class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">Are both scopes complete?</h2>
          <p class="bench__scope">
            Two ratings only compare when both count the same modules. A module declared without a result on one side
            is either missing or reported inside another.
          </p>
        </div>
        <!-- Only the modules where the two differ: the rest count the same on both sides. -->
        <p v-if="moduleDiffs.length === 0">
          Both declare the same modules with the same results, so the two ratings count the same scope.
        </p>
        <table v-else class="bench__diffs">
          <thead>
            <tr>
              <th scope="col">Module</th>
              <th scope="col"><span class="bench__swatch bench__swatch--a" />{{ a.code }}</th>
              <th scope="col"><span class="bench__swatch bench__swatch--b" />{{ b.code }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in moduleDiffs" :key="row.module">
              <th scope="row">{{ row.module }}</th>
              <td>{{ row.a }}</td>
              <td>{{ row.b }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import type { BenchmarkMark, ModuleCheck } from '@/api/overview';
import CeilingRuler from '@/components/CeilingRuler.vue';
import PairedBars from '@/components/PairedBars.vue';
import RatingLabel from '@/components/RatingLabel.vue';
import { bothScope, pairRows, projectName } from '@/compare';
import { useOverviewPair } from '@/composables/useOverview';
import { one } from '@/format';

const { a, b, error } = useOverviewPair();

const sides = computed(() =>
  a.value && b.value
    ? [
        { key: 'a', o: a.value },
        { key: 'b', o: b.value },
      ]
    : [],
);

// Each scale either building is placed on, with both placements; the scale itself
// (bands, scope, source) is the same for both, so it is read from whichever has it.
const scales = computed(() =>
  ['leti', 're2020'].flatMap((key) => {
    const placed = sides.value.map((s) => ({
      key: s.key,
      name: projectName(s.o),
      benchmark: s.o.benchmarks.find((x) => x.key === key),
    }));
    const scale = placed.find((p) => p.benchmark)?.benchmark;
    const marks = placed.map<BenchmarkMark>((p) => ({
      key: p.key as 'a' | 'b',
      value: p.benchmark?.value ?? null,
      band: p.benchmark?.band ?? null,
    }));
    return scale ? [{ ...scale, sides: placed, marks }] : [];
  }),
);

const placedScales = computed(() => scales.value.filter((s) => s.marks.some((m) => m.value !== null)));
const unplacedScales = computed(() => scales.value.filter((s) => s.marks.every((m) => m.value === null)));


// As ModuleChecks labels them.
const moduleState = (c: ModuleCheck | undefined) => {
  if (!c) return 'Not listed';
  if (c.status === 'declared_no_result') return 'Declared, no result';
  if (c.status === 'result_not_declared') return 'Results, not declared';
  return c.declared ? 'Declared, has results' : 'Not in scope';
};
const moduleDiffs = computed(() => {
  if (!a.value || !b.value) return [];
  const inB = new Map(b.value.module_checks.map((c) => [c.module, c]));
  const modules = [...new Set([...a.value.module_checks, ...b.value.module_checks].map((c) => c.module))];
  const inA = new Map(a.value.module_checks.map((c) => [c.module, c]));
  return modules
    .map((module) => ({ module, a: moduleState(inA.get(module)), b: moduleState(inB.get(module)) }))
    .filter((row) => row.a !== row.b);
});

const elementRows = computed<ComparedRow[]>(() =>
  a.value && b.value
    ? pairRows(a.value, b.value, (o) => [...o.elements, o.other_classified, o.not_classified], (e) => e.element, (e) => e.gwp)
    : [],
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.bench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: tokens.$spacing-page;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.bench__aside {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
}

.bench__aside p {
  margin: 0;
}

.bench__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.bench__verdict {
  font-size: tokens.$text-size-lg;
}

.bench__scope,
.bench__source {
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.bench__none {
  display: block;
  margin: 0;
  color: tokens.$color-text-muted;
}

.bench__diffs {
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
}

.bench__diffs th,
.bench__diffs td {
  padding: tokens.$spacing-xs tokens.$spacing-lg tokens.$spacing-xs 0;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
}

.bench__diffs thead th {
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
}

.bench__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
}

.bench__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.bench__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
}

@media (max-width: 1199px) {
  .bench {
    grid-template-columns: minmax(0, 1fr);
    gap: tokens.$spacing-xl;
  }
}
</style>

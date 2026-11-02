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

      <section v-for="scale in scales" :key="scale.key" class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">{{ scale.name }}</h2>
          <p v-for="side in scale.sides" :key="side.key" class="bench__verdict">
            <span class="bench__swatch" :class="`bench__swatch--${side.key}`" />{{ side.name }}:
            <strong>{{ side.benchmark?.band ?? 'not placed' }}</strong>
            <template v-if="side.benchmark && side.benchmark.value !== null">
              at {{ one.format(side.benchmark.value) }} kg CO₂e per m²
            </template>
          </p>
          <p class="bench__scope">{{ scale.scope }}</p>
          <p class="bench__source">
            Source: <a class="link" :href="scale.source_url" target="_blank" rel="noopener">{{ scale.source }}</a>
          </p>
        </div>

        <!-- The scale once, each building marked on it. -->
        <RatingLabel v-if="scale.key === 'leti'" :benchmark="scale" :marks="scale.marks" />
        <CeilingRuler v-else-if="scale.marks.some((m) => m.value !== null)" :benchmark="scale" :marks="scale.marks" />
        <p v-else class="u-text-muted">
          Neither building declares a useful floor area, so RE2020 cannot place them.
        </p>
      </section>

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
          :a-label="projectName(a)"
          :b-label="projectName(b)"
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
        <div class="grid-2-col">
          <div v-for="side in sides" :key="side.key" class="bench__checks">
            <p class="bench__who"><span class="bench__swatch" :class="`bench__swatch--${side.key}`" />{{ projectName(side.o) }}</p>
            <ModuleChecks
              :checks="side.o.module_checks"
              :rows-read="side.o.rows_read"
              :declared-without-result="side.o.modules_declared_without_result"
              :result-without-declaration="side.o.modules_with_undeclared_result"
            />
          </div>
        </div>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import type { BenchmarkMark } from '@/api/overview';
import CeilingRuler from '@/components/CeilingRuler.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import PairedBars from '@/components/PairedBars.vue';
import RatingLabel from '@/components/RatingLabel.vue';
import { pairRows, projectName } from '@/compare';
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

.bench__aside p,
.bench__who {
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

.bench__checks {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
}

.bench__who {
  font-weight: tokens.$text-weight-bold;
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

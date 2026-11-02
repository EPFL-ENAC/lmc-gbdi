<template>
  <!-- Passport, for two buildings: each one as the materials it is made of, two walls
       apiece (mass, carbon), with one colour per OpenBDF material class across both, so
       the same class reads the same in all four walls. Then the classes per m². -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Loading both buildings…</p>

    <template v-else>
      <header>
        <h1>
          {{ projectName(a) }} and {{ projectName(b) }}<br />
          <span class="text-display-lead">Material passports</span>
        </h1>
        <p class="text-lead">
          Custom material names never match across projects; the OpenBDF material class does. One brick is one per
          cent of the building's own total.
        </p>
      </header>

      <section class="passport__section">
        <h2 class="passport__title">What each weighs, what each emits</h2>
        <!-- No A/B swatch here: inside the walls, colour means the material class. -->
        <div class="grid-2-col passport__walls">
          <article v-for="side in sides" :key="side.key" class="passport__side">
            <p class="passport__who">
              {{ projectName(side.o) }}
            </p>
            <figure class="passport__wall">
              <figcaption>
                Mass, <strong>{{ figure(perM2(side.o, side.o.total_mass_kg), kg) }}</strong> kg per m²
              </figcaption>
              <BrickWall :parts="wall(side.o, 'mass_kg')" :label="`Mass by material class, ${projectName(side.o)}`" />
            </figure>
            <figure class="passport__wall">
              <figcaption>
                Whole-life carbon, <strong>{{ figure(perM2(side.o, side.o.headline.whole_life), kg) }}</strong> kg CO₂e
                per m²
              </figcaption>
              <BrickWall :parts="wall(side.o, 'gwp')" :label="`Whole-life carbon by material class, ${projectName(side.o)}`" />
            </figure>
          </article>
        </div>
        <ul class="passport__legend" aria-label="Material classes">
          <li v-for="c in classes" :key="c.label">
            <span class="passport__brick" :style="{ background: c.color }" />{{ c.label }}
          </li>
          <li><span class="passport__brick" :style="{ background: OTHER_COLOR }" />Every other class</li>
        </ul>
      </section>

      <section class="passport__section">
        <h2 class="passport__title">Class by class, per m²</h2>
        <p class="u-text-muted">Heavy is not the same as intense: the two lists rarely rank the same.</p>
        <div class="grid-2-col">
          <PairedBars :rows="classMass" :a-label="projectName(a)" :b-label="projectName(b)" unit="kg per m²" caption="Mass of each material class." />
          <PairedBars :rows="classCarbon" :a-label="projectName(a)" :b-label="projectName(b)" unit="kg CO₂e per m²" caption="Whole-life carbon of each material class, modules A to C." />
        </div>
      </section>

      <section class="passport__section">
        <h2 class="passport__title">How the data was declared</h2>
        <p v-for="side in sides" :key="side.key">
          {{ projectName(side.o) }}:
          {{ kg.format(side.o.rows_read) }} rows, data from {{ side.o.project.lca_database ?? 'an undeclared database' }}.
          {{ dataTypeSentence(side.o) }}
        </p>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import type { Overview } from '@/api/overview';
import BrickWall, { type WallPart } from '@/components/BrickWall.vue';
import PairedBars from '@/components/PairedBars.vue';
import { pairRows, perM2, projectName } from '@/compare';
import { useOverviewPair } from '@/composables/useOverview';
import { MATERIAL_COLORS, OTHER_COLOR } from '@/dataviz';
import { figure, kg, percent, WEIGHTING } from '@/format';

const { a, b, error } = useOverviewPair();

const sides = computed(() =>
  a.value && b.value
    ? [
        { key: 'a', o: a.value },
        { key: 'b', o: b.value },
      ]
    : [],
);

// The classes that weigh most in either building, by their share of its mass plus their
// share of its carbon, one colour each; the rest are "every other class".
const classes = computed(() => {
  if (!a.value || !b.value) return [];
  const score = new Map<string, number>();
  for (const o of [a.value, b.value]) {
    const mass = o.material_classes.reduce((s, c) => s + c.mass_kg, 0) || 1;
    const gwp = o.headline.whole_life || 1;
    for (const c of o.material_classes) {
      score.set(c.label, (score.get(c.label) ?? 0) + Math.max(c.mass_kg / mass, 0) + Math.max(c.gwp / gwp, 0));
    }
  }
  return [...score]
    .sort((x, y) => y[1] - x[1])
    .slice(0, MATERIAL_COLORS.length)
    .map(([label], i) => ({ label, color: MATERIAL_COLORS[i]! }));
});

// A wall in the shared class order, each class as its share of this building's total.
const wall = (o: Overview, measure: 'mass_kg' | 'gwp'): WallPart[] => {
  const total = measure === 'gwp' ? o.headline.whole_life : o.material_classes.reduce((s, c) => s + c.mass_kg, 0);
  const of = new Map(o.material_classes.map((c) => [c.label, c[measure]]));
  return classes.value.map((c) => ({ color: c.color, share: total ? (of.get(c.label) ?? 0) / total : 0 }));
};

const pair = (value: (c: Overview['material_classes'][number]) => number) =>
  computed<ComparedRow[]>(() =>
    a.value && b.value ? pairRows(a.value, b.value, (o) => o.material_classes, (c) => c.label, value) : [],
  );
const classMass = pair((c) => c.mass_kg);
const classCarbon = pair((c) => c.gwp);

const dataTypeSentence = (o: Overview) => {
  const undeclared = o.data_types.find((d) => d.key === 'undeclared')?.share;
  const lead = undeclared === undefined ? '' : `Data type undeclared: ${percent.format(undeclared)}. `;
  return `${lead}${WEIGHTING[o.data_type_weighting]}`;
};
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.passport__section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.passport__section p {
  margin: 0;
}

.passport__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.passport__walls {
  column-gap: tokens.$spacing-page;
}

.passport__side {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}

.passport__who {
  font-weight: tokens.$text-weight-bold;
}

.passport__wall {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
  margin: 0;
  font-size: tokens.$text-size-sm;
}

.passport__wall strong {
  font-variant-numeric: tabular-nums;
}




.passport__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-sm tokens.$spacing-lg;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-sm;
}

.passport__brick {
  display: inline-block;
  width: tokens.$spacing-lg;
  height: tokens.$spacing-sm;
  margin-right: tokens.$spacing-sm;
  border-radius: tokens.$radius-xs;
}
</style>

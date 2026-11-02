<template>
  <!-- Section, for two buildings: one statement setting the two figures per m² against
       each other, then both buildings drawn as sections on one scale, so the taller
       drawing is the one that emits more per m², then the life cycle and the materials. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Loading both buildings…</p>

    <template v-else>
      <header>
        <p class="section-page__name">
          {{ projectName(a) }} and
          {{ projectName(b) }}
        </p>
        <h1 class="section-page__statement">
          {{ figure(perM2(a, a.headline.whole_life), kg) }} against {{ figure(perM2(b, b.headline.whole_life), kg) }}
          kg CO₂e per m<sup>2</sup>
          <span class="text-display-lead">{{ lead }}</span>
        </h1>
      </header>

      <section class="section-page__block">
        <h2 class="section-page__title">Where it sits in each building</h2>
        <!-- Both on one ground line, so their heights read against each other. No A/B
             swatch here: inside the drawing, colour means the life-cycle stage. -->
        <div class="grid-2-col section-page__pair">
          <div v-for="side in sides" :key="side.key">
            <p class="section-page__who">
              {{ projectName(side.o) }}
            </p>
            <BuildingSection
              :stages="side.o.stages"
              :elements="side.o.elements"
              :element-stages="side.o.element_stages"
              :not-classified="side.o.not_classified"
              :rem-per-kg="side.remPerKg"
            >
              <template #caption>
                <template v-if="side.remPerKg">
                  Both drawn on one scale per m² of gross floor area: the taller building emits more per m².
                </template>
                <template v-else>A gross floor area is missing: each building fills its own height.</template>
                Figures in kg CO₂e for the whole building.
              </template>
            </BuildingSection>
          </div>
        </div>
      </section>

      <section class="section-page__block">
        <h2 class="section-page__title">When it is emitted</h2>
        <PairedBars
          :rows="stageRows"
          :a-label="projectName(a)"
          :b-label="projectName(b)"
          unit="kg CO₂e per m²"
          caption="Below zero: carbon stored or credited, most often biogenic carbon in timber."
        />
      </section>

      <section class="section-page__block">
        <h2 class="section-page__title">What it is made of</h2>
        <div class="grid-2-col">
          <PairedBars :rows="classCarbon" :a-label="projectName(a)" :b-label="projectName(b)" unit="kg CO₂e per m²" caption="By whole-life carbon, per OpenBDF material class." />
          <PairedBars :rows="classMass" :a-label="projectName(a)" :b-label="projectName(b)" unit="kg per m²" caption="By mass, per OpenBDF material class." />
        </div>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import type { Overview } from '@/api/overview';
import BuildingSection from '@/components/BuildingSection.vue';
import PairedBars from '@/components/PairedBars.vue';
import { pairRows, perM2, projectName } from '@/compare';
import { useOverviewPair } from '@/composables/useOverview';
import { figure, kg, percent } from '@/format';

const { a, b, error } = useOverviewPair();

const HEIGHT_REM = 26; // the taller building, as on the single Section page

// The drawn height of a building per m²: every band, by magnitude, as BuildingSection draws it.
const drawnPerM2 = (o: Overview) =>
  perM2(o, [...o.elements, o.not_classified].reduce((sum, e) => sum + Math.abs(e.gwp), 0));

const sides = computed(() => {
  if (!a.value || !b.value) return [];
  const pa = drawnPerM2(a.value);
  const pb = drawnPerM2(b.value);
  const tallest = pa !== null && pb !== null ? Math.max(pa, pb) : 0;
  // Rem per kg: the tallest per m² fills HEIGHT_REM; each divides by its own area.
  const scale = (o: Overview) => (tallest > 0 ? HEIGHT_REM / (tallest * o.project.gross_floor_area_m2!) : undefined);
  return [
    { key: 'a', o: a.value, remPerKg: scale(a.value) },
    { key: 'b', o: b.value, remPerKg: scale(b.value) },
  ];
});

const lead = computed(() => {
  if (!a.value || !b.value) return '';
  const ra = perM2(a.value, a.value.headline.whole_life);
  const rb = perM2(b.value, b.value.headline.whole_life);
  if (ra === null || rb === null || ra === 0) return 'A gross floor area is missing.';
  return `the second at ${percent.format(rb / ra)} of the first, over the whole life`;
});

const pair = <T,>(pick: (o: Overview) => T[], label: (r: T) => string, value: (r: T) => number) =>
  computed<ComparedRow[]>(() => (a.value && b.value ? pairRows(a.value, b.value, pick, label, value) : []));

const stageRows = pair((o) => o.stages, (s) => s.label, (s) => s.gwp);
const classCarbon = pair((o) => o.material_classes, (m) => m.label, (m) => m.gwp);
const classMass = pair((o) => o.material_classes, (m) => m.label, (m) => m.mass_kg);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.section-page__name {
  margin: 0 0 tokens.$spacing-sm;
  font-size: tokens.$text-size-heading-lg;
}

.section-page__statement {
  margin: 0;
  font-size: tokens.$text-size-display-lg;
}

.section-page__statement .text-display-lead {
  display: block;
}

// SK Modernist has no ² glyph: a sized-down 2 instead.
.section-page__statement sup {
  font-size: 0.45em;
  line-height: 0;
}

.section-page__block {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.section-page__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.section-page__pair {
  align-items: end;
}

.section-page__who {
  margin: 0 0 tokens.$spacing-md;
  font-weight: tokens.$text-weight-bold;
}



</style>

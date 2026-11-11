<template>
  <!-- Two buildings on the same footing: per m² of gross floor area, stage by stage,
       element by element, material class by material class. -->
  <q-page class="page-grid">
    <header class="compare__head">
      <h1 v-if="comparison">
        {{ named(comparison.a) }} and {{ named(comparison.b) }}<br />
        <span class="text-display-lead">per m<sup>2</sup> of gross floor area</span>
      </h1>
      <h1 v-else>Compare two buildings</h1>
      <!-- Inside a building the building bar picks; /buildings/compare picks here. -->
      <div v-if="!inBuilding" class="compare__pickers">
        <q-select
          v-for="side in SIDES"
          :key="side"
          :model-value="side === 'a' ? a : b"
          :options="options"
          option-label="label"
          option-value="id"
          emit-value
          map-options
          dense
          outlined
          :label="side === 'a' ? 'Building' : 'Compared with'"
          class="compare__picker"
          @update:model-value="(id: number) => pick(side, id)"
        />
      </div>
    </header>

    <p v-if="error" class="gbdi-card" role="alert">The comparison could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Pick two buildings.</p>
    <p v-else-if="comparison === null" class="u-text-muted">Loading the comparison…</p>

    <template v-else>
      <section class="duel" aria-label="Whole-life carbon per m²">
        <article v-for="side in SIDES" :key="side" class="duel__side">
          <p class="duel__code">
            <span class="duel__swatch" :class="`duel__swatch--${side}`" />
            <router-link class="link" :to="`/buildings/${comparison[side].id}`">{{ code(comparison[side]) }}</router-link>
          </p>
          <p class="duel__name">
            {{ comparison[side].project_name ?? 'Unnamed project' }}, {{ comparison[side].country ?? 'country not declared' }}
          </p>
          <p class="duel__figure">{{ figure(comparison[side].whole_life_per_m2, kg) }}</p>
          <p>kg CO₂e per m² over the whole life, modules A to C.</p>
          <dl class="duel__facts">
            <div><dt>Gross floor area</dt><dd>{{ figure(comparison[side].gross_floor_area_m2, kg) }} m²</dd></div>
            <div><dt>Upfront, A1–A5</dt><dd>{{ figure(comparison[side].upfront_per_m2, kg) }} kg/m²</dd></div>
            <div><dt>Beyond, D1</dt><dd>{{ figure(comparison[side].module_d1_per_m2, kg) }} kg/m²</dd></div>
            <div><dt>Lines read</dt><dd>{{ kg.format(comparison[side].rows_read) }}</dd></div>
          </dl>
        </article>
      </section>
      <p v-if="comparison.ratio !== null" class="text-lead">
        Per m², {{ named(comparison.b) }} emits {{ percent.format(comparison.ratio) }} of what
        {{ named(comparison.a) }} emits over its whole life.
      </p>

      <section class="compare__section">
        <h2 class="compare__title">Life-cycle stages</h2>
        <PairedBars
          :rows="comparison.stages"
          :a-label="code(comparison.a)"
          :b-label="code(comparison.b)"
          unit="kg CO₂e per m²"
          caption="Below zero: carbon stored or credited, most often biogenic carbon in timber at A1–A3, released again at C3–C4."
        />
      </section>

      <section class="compare__section">
        <h2 class="compare__title">Building elements</h2>
        <PairedBars
          :rows="comparison.elements"
          :a-label="code(comparison.a)"
          :b-label="code(comparison.b)"
          unit="kg CO₂e per m²"
          caption="OpenBDF Tier 2 elements, whole life. Lines without an element code stay visible as Not classified."
        />
      </section>

      <section class="compare__section">
        <h2 class="compare__title">Materials, by OpenBDF class</h2>
        <p class="u-text-muted">
          Custom material names never match across projects; the OpenBDF material class does. Carbon and mass rarely
          rank the same.
        </p>
        <div class="grid-2-col">
          <PairedBars
            :rows="comparison.material_carbon"
            :a-label="code(comparison.a)"
            :b-label="code(comparison.b)"
            unit="kg CO₂e per m²"
            caption="Whole-life carbon of each material class."
          />
          <PairedBars
            :rows="comparison.material_mass"
            :a-label="code(comparison.a)"
            :b-label="code(comparison.b)"
            unit="kg per m²"
            caption="Mass of each material class."
          />
        </div>
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { buildingPath } from '@/buildingLayouts';
import { code, fetchBuildings, fetchComparison, noCarbon, type BuildingSummary, type ComparedBuilding, type Comparison } from '@/api/buildings';
import PairedBars from '@/components/PairedBars.vue';
import { figure, kg, percent } from '@/format';

const SIDES = ['a', 'b'] as const;
// As every compare page: "Iewan (NL-23)" in words, the code alone in legends.
const named = (x: ComparedBuilding) => `${x.project_name ?? 'Unnamed project'} (${code(x)})`;

const route = useRoute();
const router = useRouter();
const buildings = ref<BuildingSummary[]>([]);
const comparison = ref<Comparison | null>(null);
const error = ref<string | null>(null);

const idOf = (value: unknown) => (typeof value === 'string' && value !== '' ? Number(value) : null);
const inBuilding = computed(() => route.params.id !== undefined);
const a = computed(() => idOf(inBuilding.value ? route.params.id : route.query.a));
const b = computed(() => idOf(inBuilding.value ? route.params.other : route.query.b));
const options = computed(() =>
  buildings.value.filter((x) => !noCarbon(x)).map((x) => ({ id: x.id, label: `${code(x)}, ${x.project_name ?? 'unnamed'}` })),
);

// Once both are picked, the comparison lives under the first building, in its layouts.
const pick = (side: 'a' | 'b', id: number) => {
  const next = { a: a.value, b: b.value, [side]: id };
  if (next.a !== null && next.b !== null) void router.replace(buildingPath(next.a, '', next.b));
  else void router.replace({ query: { ...route.query, [side]: id } });
};

onMounted(async () => {
  try {
    buildings.value = await fetchBuildings();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

watch(
  [a, b],
  async ([ia, ib]) => {
    comparison.value = null;
    error.value = null;
    if (ia === null || ib === null) return;
    try {
      comparison.value = await fetchComparison(ia, ib);
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.compare__head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: tokens.$spacing-xl;
}

.compare__head h1 {
  margin: 0;
}

// SK Modernist has no ² glyph: a sized-down 2 instead.
.compare__head sup {
  font-size: 0.45em;
  line-height: 0;
}

.compare__pickers {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: tokens.$spacing-md;
}

.compare__picker {
  min-width: 16rem;
}

.duel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  border-top: tokens.$border-width solid tokens.$color-border;
  border-bottom: tokens.$border-width solid tokens.$color-border;
}

.duel__side {
  padding: tokens.$spacing-xl tokens.$spacing-xl tokens.$spacing-xl 0;
}

.duel__side + .duel__side {
  padding-left: tokens.$spacing-xl;
  border-left: tokens.$border-width solid tokens.$color-border;
}

.duel__side p {
  margin: 0;
}

.duel__code {
  margin: 0;
  font-weight: tokens.$text-weight-bold;
}

.duel__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
}

.duel__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.duel__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
}

.duel__name {
  color: tokens.$color-text-muted;
}

.duel__figure {
  padding-top: tokens.$spacing-lg;
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-lg;
  line-height: tokens.$text-line-height-tight;
  font-variant-numeric: tabular-nums;
}

.duel__facts {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: tokens.$spacing-md;
  margin: tokens.$spacing-lg 0 0;
}

.duel__facts dt {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.duel__facts dd {
  margin: 0;
  font-variant-numeric: tabular-nums;
}

.compare__section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.compare__section > p {
  margin: 0;
}

.compare__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

@media (max-width: 1199px) {
  .duel,
  .duel__facts {
    grid-template-columns: minmax(0, 1fr);
  }

  .duel__side + .duel__side {
    padding-left: 0;
    border-left: 0;
    border-top: tokens.$border-width solid tokens.$color-border;
  }
}
</style>

<template>
  <!-- Two buildings on the same footing: per m² of gross floor area, stage by stage,
       element by element, material class by material class. -->
  <q-page class="sheet-page">
    <article class="sheet">
      <header class="sheet__title compare__head">
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
        <!-- Case 3 only: the building bar holds the choice, beside the pickers; the
             standalone page has no bar and keeps it here. -->
        <Teleport v-if="comparison?.case === 'different_stages'" defer to="#basis-control" :disabled="!inBuilding">
          <div class="compare__scope" role="group" aria-labelledby="compare-scope-label">
            <span id="compare-scope-label" class="compare__scope-label">Totals on</span>
            <q-btn-toggle
              v-model="scope"
              :options="SCOPES"
              no-caps
              unelevated
              dense
              toggle-color="primary"
              color="white"
              text-color="dark"
              class="compare__scope-toggle"
            />
          </div>
        </Teleport>
        <!-- Below 600 px the choice folds behind the bar's Display button, which still
             names it; the banner below says it too. -->
        <Teleport
          v-if="$q.screen.lt.sm && inBuilding && comparison?.case === 'different_stages'"
          defer
          to="#display-summary"
          >{{ `: ${SCOPES.find((o) => o.value === scope)?.short}` }}</Teleport
        >
      </header>

      <p v-if="error" class="sheet__panel" role="alert">The comparison could not be loaded. {{ error }}</p>
      <p v-else-if="a === null || b === null" class="sheet__panel u-text-muted">Pick two buildings.</p>
      <p v-else-if="comparison === null" class="sheet__panel u-text-muted">Loading the comparison…</p>

      <template v-else>
        <!-- What the figures below cover, and the other choice one click away. -->
        <p v-if="comparison.case === 'different_stages'" class="compare__banner" role="status">
          <template v-if="comparison.applied_scope === 'common'">
            Compared on the stages both cover: {{ comparison.common_stages.join(', ') }}.
            <template v-for="out in comparison.left_out" :key="out.stage">
              {{ out.stage }} is left out: {{ named(comparison[out.not_covered_by]) }} does not cover it.
            </template>
          </template>
          <template v-else>Each building on its own scope: the totals do not cover the same stages.</template>
          <q-btn
            flat
            dense
            no-caps
            color="primary"
            class="compare__switch"
            :label="comparison.applied_scope === 'common' ? 'Show each on its own scope' : 'Compare on the stages both cover'"
            @click="scope = comparison.applied_scope === 'common' ? 'own' : 'common'"
          />
        </p>
        <MethodNotice :comparison="comparison" />
        <section class="sheet__panel" aria-label="Carbon per m²">
          <div class="duel">
            <article v-for="side in SIDES" :key="side" class="duel__side">
              <p class="duel__code">
                <span class="duel__swatch" :class="`duel__swatch--${side}`" />
                <router-link class="link" :to="`/buildings/${comparison[side].id}`">{{ code(comparison[side]) }}</router-link>
              </p>
              <p class="duel__name">
                {{ comparison[side].project_name ?? 'Unnamed project' }}, {{ comparison[side].country ?? 'country not declared' }}
                <DraftBadge :building-id="comparison[side].id" />
              </p>
              <p class="duel__figure">{{ figure(comparison[side].whole_life_per_m2, kg) }}</p>
              <p>
                kg CO₂e per m²<template v-if="comparison.applied_scope === 'own'">, {{ comparison[side].scope }}</template>.
              </p>
              <!-- The stages this figure stands for, named on every headline number. -->
              <ul class="duel__stages" :aria-label="`Stages in ${code(comparison[side])}'s figure`">
                <li v-for="stage in comparison[`stages_${side}`]" :key="stage" class="duel__stage">{{ stage }}</li>
              </ul>
              <dl class="duel__facts">
                <div><dt>Gross floor area</dt><dd>{{ figure(comparison[side].gross_floor_area_m2, kg) }} m²</dd></div>
                <div><dt>Upfront, {{ comparison.upfront_stages.join(', ') || 'no stage' }}</dt><dd>{{ figure(comparison[side].upfront_per_m2, kg) }} kg/m²</dd></div>
                <!-- No module D (no scope flag, no result): nothing, not 0. -->
                <div v-if="comparison[side].has_module_d">
                  <dt>Module D, outside the total</dt>
                  <dd>{{ figure(comparison[side].module_d_per_m2, kg) }} kg/m²</dd>
                </div>
                <!-- Declared, apart from the computed scope above: a reader sees when two columns differ. -->
                <div><dt>System boundary</dt><dd>{{ comparison[side].system_boundary ?? 'not declared' }}</dd></div>
                <div><dt>LCIA methodology</dt><dd>{{ comparison[side].lcia_methodology ?? 'not declared' }}</dd></div>
                <div><dt>Lines read</dt><dd>{{ kg.format(comparison[side].rows_read) }}</dd></div>
              </dl>
            </article>
          </div>
          <!-- Only when both figures cover the same stages, and it names them. -->
          <p v-if="comparison.ratio !== null && comparison.ratio_stages" class="text-lead">
            On {{ comparison.ratio_stages.join(', ') }}, per m², {{ named(comparison.b) }} emits
            {{ percent.format(comparison.ratio) }} of what {{ named(comparison.a) }} emits.
          </p>
        </section>

        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Life-cycle stages</h2>
          <component
            :is="bars"
            :rows="comparison.stages"
            :a="comparison.a"
            :b="comparison.b"
            unit="kg CO₂e per m²"
            caption="Below zero: carbon stored or credited, most often biogenic carbon in timber at A1–A3, released again at C3–C4."
          />
          <p v-for="out in merged ? comparison.left_out : []" :key="out.stage" class="u-text-muted">
            {{ out.stage }}: left out. {{ code(comparison[out.not_covered_by === 'a' ? 'b' : 'a']) }}
            {{ out.value === null ? 'no floor area' : kg.format(out.value) }} kg/m²,
            {{ code(comparison[out.not_covered_by]) }} not covered.
          </p>
        </section>

        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Building elements</h2>
          <component
            :is="bars"
            :rows="comparison.elements"
            :a="comparison.a"
            :b="comparison.b"
            unit="kg CO₂e per m²"
            caption="OpenBDF Tier 2 elements, total carbon. Lines without an element code stay visible as Not classified."
          />
        </section>

        <section class="sheet__panel">
          <h2 class="sheet__panel-title">Materials, by OpenBDF class</h2>
          <p class="u-text-muted">
            Custom material names never match across projects; the OpenBDF material class does. Carbon and mass rarely
            rank the same.
          </p>
          <component
            :is="bars"
            :rows="comparison.material_carbon"
            :a="comparison.a"
            :b="comparison.b"
            unit="kg CO₂e per m²"
            caption="Carbon of each material class."
          />
          <component
            :is="bars"
            :rows="comparison.material_mass"
            :a="comparison.a"
            :b="comparison.b"
            unit="kg per m²"
            caption="Mass of each material class."
          />
        </section>
      </template>
    </article>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { buildingPath } from '@/buildingLayouts';
import {
  code,
  fetchBuildings,
  fetchComparison,
  noCarbon,
  type BuildingSummary,
  type ComparedBuilding,
  type CompareScope,
  type Comparison,
} from '@/api/buildings';
import DraftBadge from '@/components/DraftBadge.vue';
import MethodNotice from '@/components/MethodNotice.vue';
import GroupedBars from '@/components/GroupedBars.vue';
import PairedBars from '@/components/PairedBars.vue';
import { figure, kg, percent } from '@/format';

const SIDES = ['a', 'b'] as const;
// The backend says when both figures cover the same stages: one axis then, else one each.
const merged = computed(() => comparison.value?.applied_scope === 'common');
const bars = computed(() => (merged.value ? GroupedBars : PairedBars));
const SCOPES: { value: CompareScope; label: string; short: string }[] = [
  { value: 'common', label: 'Common stages', short: 'Common stages' },
  { value: 'own', label: 'Each on its own scope', short: 'Own scope' },
];
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
// ?scope=own, or the default: the stages both cover. The other query and the hash stay.
const scope = computed<CompareScope>({
  get: () => (route.query.scope === 'own' ? 'own' : 'common'),
  set: (next) =>
    void router.replace({ query: { ...route.query, scope: next === 'own' ? 'own' : undefined }, hash: route.hash }),
});
const options = computed(() =>
  buildings.value.filter((x) => !noCarbon(x)).map((x) => ({ id: x.id, label: `${code(x)}, ${x.project_name ?? 'unnamed'}` })),
);

// Once both are picked, the comparison lives under the first building, in its layouts.
const pick = (side: 'a' | 'b', id: number) => {
  const next = { a: a.value, b: b.value, [side]: id };
  if (next.a !== null && next.b !== null) void router.replace(buildingPath(next.a, next.b));
  else void router.replace({ query: { ...route.query, [side]: id } });
};

onMounted(async () => {
  try {
    buildings.value = await fetchBuildings();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

// Another pair empties the page; another scope keeps it until the answer comes. Only
// the last request's answer lands.
let asked = 0;
watch(
  [a, b, scope],
  async ([ia, ib, sc], old) => {
    const n = ++asked;
    if (old === undefined || ia !== old[0] || ib !== old[1]) comparison.value = null;
    error.value = null;
    if (ia === null || ib === null) return;
    try {
      const next = await fetchComparison(ia, ib, sc);
      if (n === asked) comparison.value = next;
    } catch (e: unknown) {
      if (n === asked) error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.compare__head {
  display: flex;
  flex-direction: row;
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

.compare__scope {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: tokens.$spacing-sm;
}

.compare__scope-label {
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.compare__scope-toggle {
  border: tokens.$border-width solid tokens.$color-border;
}

.compare__banner {
  margin: 0;
  padding: tokens.$spacing-sm tokens.$spacing-lg;
  border-left: 4px solid var(--gbdi-dataviz-blue-2);
  background: tokens.$color-surface-highlight;
  font-size: tokens.$text-size-sm;
}

.compare__switch {
  margin-left: tokens.$spacing-xs;
  text-decoration: underline;
}

.duel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.duel__side {
  padding-right: tokens.$spacing-xl;
}

.duel__side + .duel__side {
  padding-left: tokens.$spacing-xl;
  border-left: tokens.$border-width solid tokens.$color-border;
}

.duel__side p {
  margin: 0;
}

.duel__stages {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-xs;
  margin: 0 0 tokens.$spacing-md;
  padding: 0;
  list-style: none;
}

.duel__stage {
  padding: 0 tokens.$spacing-sm;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: 999px;
  font-size: tokens.$text-size-xs;
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

@media (max-width: 1199px) {
  .duel,
  .duel__facts {
    grid-template-columns: minmax(0, 1fr);
  }

  .duel__side + .duel__side {
    padding-top: tokens.$spacing-xl;
    padding-left: 0;
    border-left: 0;
    border-top: tokens.$border-width solid tokens.$color-border;
  }
}
</style>
